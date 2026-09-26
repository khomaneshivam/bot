import time
import uuid
from typing import Dict, List, Optional, Any
from bot.config.settings import settings
from bot.storage.db import db
from bot.execution.models import (
    ExecutionMode,
    OrderStatus,
    OrderRequest,
    OrderResult,
    BrokerPosition
)
from bot.execution.adapters.base import BaseExecutionAdapter
from bot.execution.adapters.paper import PaperExecutionAdapter
from bot.execution.adapters.mt5 import MT5ExecutionAdapter
from bot.execution.adapters.binance import BinanceExecutionAdapter
from bot.execution.order_state import order_state_machine
from bot.execution.reconciliation import reconciliation_service, ReconciliationReport
from bot.risk.circuit_breakers import circuit_breaker_manager

class ExecutionService:
    """
    Central execution service coordinating broker adapters, order state transitions,
    fail-closed risk protections, and state persistence.
    """

    def __init__(self, mode: ExecutionMode = ExecutionMode.PAPER):
        self.mode = mode
        self.adapter: BaseExecutionAdapter = self._initialize_adapter(mode)
        self.circuit_breaker_tripped = False

    def _initialize_adapter(self, mode: ExecutionMode) -> BaseExecutionAdapter:
        if mode == ExecutionMode.PAPER:
            return PaperExecutionAdapter(starting_balance=settings.PAPER_STARTING_BALANCE)
        elif mode in (ExecutionMode.MT5_DEMO, ExecutionMode.MT5_LIVE):
            return MT5ExecutionAdapter(mode=mode)
        elif mode in (ExecutionMode.BINANCE_TESTNET, ExecutionMode.BINANCE_LIVE):
            return BinanceExecutionAdapter(mode=mode)
        else:
            return PaperExecutionAdapter()

    def set_execution_mode(self, new_mode: ExecutionMode) -> None:
        """
        Switches the execution mode with strict safety checks.
        Refuses live modes unless explicit live authorization flags are enabled.
        """
        if new_mode.is_live() and not settings.ALLOW_LIVE_TRADING:
            raise PermissionError(
                f"Cannot switch to live mode {new_mode.value}: ALLOW_LIVE_TRADING is False in configuration."
            )

        if self.adapter:
            self.adapter.disconnect()

        self.mode = new_mode
        self.adapter = self._initialize_adapter(new_mode)
        self.adapter.connect()

    def get_open_positions(self) -> List[Dict]:
        """Loads confirmed active positions from persistent database."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM active_positions")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def submit_order(self, request: OrderRequest) -> OrderResult:
        """
        Strict fail-closed order submission workflow.
        1. Checks circuit breaker and reconciliation status.
        2. Records CREATED order in state machine (idempotent).
        3. Advances to RISK_APPROVED -> SUBMITTED.
        4. Submits to execution adapter.
        5. Evaluates result:
           - FILLED: Marks FILLED, saves confirmed active position.
           - REJECTED: Marks REJECTED, never creates active position.
           - UNKNOWN: Marks UNKNOWN, triggers reconciliation.
        """
        if circuit_breaker_manager.is_tripped() or self.circuit_breaker_tripped:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message="Execution rejected: Risk circuit breaker is TRIPPED."
            )

        if reconciliation_service.has_active_mismatch:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message="Execution rejected: Broker reconciliation desync detected."
            )

        # 1. State machine - CREATED
        order_record = order_state_machine.create_order(request)
        order_id = order_record["id"]

        # Check if already completed (Idempotency)
        if order_record["status"] in (OrderStatus.FILLED.value, OrderStatus.REJECTED.value, OrderStatus.CANCELLED.value):
            return OrderResult(
                success=order_record["status"] == OrderStatus.FILLED.value,
                status=OrderStatus(order_record["status"]),
                client_order_id=request.client_order_id,
                broker_order_id=order_record.get("broker_order_id"),
                executed_price=order_record.get("executed_price"),
                executed_quantity=float(order_record.get("quantity", 0.0))
            )

        # 2. State machine - RISK_APPROVED
        order_state_machine.transition(order_id, OrderStatus.RISK_APPROVED, reason="Passed deterministic risk checks")

        # 3. State machine - SUBMITTED
        order_state_machine.transition(order_id, OrderStatus.SUBMITTED, reason=f"Dispatched to {self.mode.value} adapter")

        # 4. Invoke Broker Adapter
        result = self.adapter.submit_order(request)

        # 5. Process result
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        if result.status == OrderStatus.FILLED:
            # Advance state machine
            order_state_machine.transition(
                order_id=order_id,
                to_status=OrderStatus.FILLED,
                reason="Broker execution confirmed",
                broker_order_id=result.broker_order_id,
                executed_price=result.executed_price
            )

            # Persist active position to database
            pos_id = f"pos_{uuid.uuid4().hex[:10]}"
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO active_positions (
                    id, order_id, broker_order_id, symbol, direction, size,
                    entry_price, current_price, sl, tp, strategy, open_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pos_id,
                order_id,
                result.broker_order_id,
                request.symbol,
                request.side.upper(),
                result.executed_quantity,
                result.executed_price,
                result.executed_price,
                request.sl,
                request.tp,
                request.strategy,
                now
            ))

            # Record in trades ledger
            cursor.execute("""
                INSERT INTO trades (
                    id, order_id, broker_order_id, symbol, side, quantity,
                    entry_price, sl, tp, strategy, market_regime, entry_time, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pos_id,
                order_id,
                result.broker_order_id,
                request.symbol,
                request.side.upper(),
                result.executed_quantity,
                result.executed_price,
                request.sl,
                request.tp,
                request.strategy,
                request.market_regime,
                now,
                "OPEN"
            ))
            conn.commit()
            conn.close()

            return result

        elif result.status == OrderStatus.REJECTED:
            # Mark REJECTED in state machine, NEVER create active position
            order_state_machine.transition(
                order_id=order_id,
                to_status=OrderStatus.REJECTED,
                reason="Broker rejected order",
                failure_reason=result.error_message
            )
            return result

        else:
            # Uncertain / Unknown / Timeout: Transition to UNKNOWN and schedule reconciliation
            order_state_machine.transition(
                order_id=order_id,
                to_status=OrderStatus.UNKNOWN,
                reason=f"Broker result uncertain: {result.error_message}",
                failure_reason=result.error_message
            )
            # Immediate reconciliation check
            reconciliation_service.reconcile(self.adapter)
            return result

    def close_position(self, position_id: str, exit_reason: str = "MANUAL") -> OrderResult:
        """Closes an active position on both broker and database."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM active_positions WHERE id = ?", (position_id,))
        pos = cursor.fetchone()
        if not pos:
            conn.close()
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=f"close_{position_id}",
                error_message=f"Position #{position_id} does not exist in active positions."
            )

        pos_dict = dict(pos)
        broker_ticket = pos_dict.get("broker_order_id") or position_id

        # Dispatch close to adapter
        close_result = self.adapter.close_position(
            position_id=broker_ticket,
            symbol=pos_dict["symbol"],
            direction=pos_dict["direction"],
            volume=float(pos_dict["size"])
        )

        if close_result.success:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            exit_price = close_result.executed_price or pos_dict["entry_price"]
            entry_price = float(pos_dict["entry_price"])
            size = float(pos_dict["size"])
            direction = pos_dict["direction"]

            # Calculate PnL
            diff = (exit_price - entry_price) if direction == "BUY" else (entry_price - exit_price)
            if "USDT" in pos_dict["symbol"]:
                gross_pnl = diff * size
            elif "XAU" in pos_dict["symbol"]:
                gross_pnl = diff * size * 100.0
            else:
                gross_pnl = diff * size * 100000.0

            net_pnl = gross_pnl - close_result.commission
            entry_p = max(entry_price, 1e-6)
            ret_pct = round(((exit_price - entry_p) / entry_p * 100.0) if direction == "BUY" else ((entry_p - exit_price) / entry_p * 100.0), 2)
            was_wrong = 1 if net_pnl < 0 else 0

            # Remove from active_positions
            cursor.execute("DELETE FROM active_positions WHERE id = ?", (position_id,))

            # Update trades table
            cursor.execute("""
                UPDATE trades SET
                    exit_price = ?,
                    close_price = ?,
                    exit_time = ?,
                    close_time = ?,
                    gross_pnl = ?,
                    net_pnl = ?,
                    pnl = ?,
                    return_pct = ?,
                    exit_reason = ?,
                    was_wrong_trade = ?,
                    status = 'CLOSED'
                WHERE id = ?
            """, (
                exit_price, exit_price, now, now, round(gross_pnl, 2),
                round(net_pnl, 2), round(net_pnl, 2), ret_pct, exit_reason,
                was_wrong, position_id
            ))

            conn.commit()

        conn.close()
        return close_result

    def reconcile(self) -> ReconciliationReport:
        """Executes full broker reconciliation."""
        return reconciliation_service.reconcile(self.adapter)

execution_service = ExecutionService(mode=ExecutionMode.PAPER)
