import time
import uuid
from typing import Dict, List, Optional, Tuple
from bot.config.settings import settings
from bot.risk.risk_manager import risk_manager
from bot.data.news_feed import news_feed
from bot.ai.ml_engine import ml_engine
from bot.ai.correlation_engine import correlation_engine
from bot.strategies.ensemble import strategy_ensemble
from bot.execution.models import (
    ExecutionMode,
    OrderStatus,
    OrderRequest,
    OrderResult,
    InstrumentSpecification
)
from bot.execution.service import execution_service
from bot.execution.trade_ledger import trade_ledger
from bot.storage.db import db

def calculate_trade_pnl(symbol: str, direction: str, entry_price: float, current_price: float, size: float) -> Tuple[float, float]:
    """
    Calculates exact institutional PnL in USD:
    - Forex currency pairs: 1 standard lot = 100,000 units.
    - Gold (XAUUSD): 1 lot = 100 oz.
    - Crypto: size in units of coin.
    """
    clean_sym = symbol.upper().replace("-", "").replace("/", "")
    is_crypto = "USDT" in clean_sym
    is_gold = "XAU" in clean_sym

    price_diff = (current_price - entry_price) if direction == "BUY" else (entry_price - current_price)

    if is_crypto:
        pnl = price_diff * size
    elif is_gold:
        units = size * 100.0
        pnl = price_diff * units
    else:
        units = size * 100000.0
        if clean_sym.startswith("USD"):
            pnl = (price_diff / max(current_price, 1e-4)) * units
        else:
            pnl = price_diff * units

    pnl = round(pnl, 2)
    entry_notional = max(1.0, entry_price * (size if is_crypto else (size * 100.0 if is_gold else size * 100000.0)))
    return_pct = round((pnl / entry_notional) * 100.0, 2)
    return pnl, return_pct

class ExecutionEngine:
    """
    Unified ExecutionEngine orchestrating trade execution, exit management,
    and portfolio tracking.
    Enforces fail-closed execution via ExecutionService.
    """

    def __init__(self):
        self.mode = settings.MODE
        self.paper_balance = settings.PAPER_STARTING_BALANCE
        self.paper_equity = settings.PAPER_STARTING_BALANCE
        self.paper_realized_pnl = 0.0
        self.winning_trades_count = 0
        self.losing_trades_count = 0
        self.open_positions: List[Dict] = []
        self.closed_trades: List[Dict] = []
        self._load_persisted_state()

    def _load_persisted_state(self):
        """Loads confirmed open positions and historical trades from persistent SQLite database."""
        try:
            self.open_positions = execution_service.get_open_positions()
            summary = trade_ledger.get_audit_summary()
            self.winning_trades_count = summary.get("wins", 0)
            self.losing_trades_count = summary.get("losses", 0)
            self.paper_realized_pnl = summary.get("net_pnl", 0.0)
            self.paper_balance = settings.PAPER_STARTING_BALANCE + self.paper_realized_pnl
            self.paper_equity = self.paper_balance
            self.closed_trades = trade_ledger.get_recent_trades(limit=50)
        except Exception as e:
            print(f"[ExecutionEngine] State recovery notice: {e}")

    def reset_capital(self, starting_balance: float = 100.0):
        """Privileged capital reset. Only to be called when explicitly authorized."""
        self.paper_balance = starting_balance
        self.paper_equity = starting_balance
        self.paper_realized_pnl = 0.0
        self.open_positions = []
        self.closed_trades = []
        self.winning_trades_count = 0
        self.losing_trades_count = 0
        trade_ledger.reset_ledger()
        risk_manager.reset_daily_baseline(starting_balance)
        print(f"[ExecutionEngine] 💰 Capital reset to ${starting_balance:.2f} in {self.mode.upper()} mode.")

    def set_mode(self, new_mode: str) -> str:
        mode_enum = ExecutionMode[new_mode.upper()] if new_mode.upper() in ExecutionMode.__members__ else ExecutionMode.PAPER
        execution_service.set_execution_mode(mode_enum)
        self.mode = new_mode.lower()
        settings.MODE = self.mode
        trade_ledger.log_risk_event("MODE_SWITCH", "SYSTEM", f"Switched mode to {new_mode.upper()}")
        print(f"[ExecutionEngine] ⚠️ Mode switched to: {new_mode.upper()}")
        return self.mode

    def get_account_summary(self) -> Dict:
        unrealized = sum(p.get("unrealized_pnl", 0.0) for p in self.open_positions)
        equity = self.paper_balance + unrealized
        self.paper_equity = equity
        risk_manager.update_equity(equity)

        total_trades = self.winning_trades_count + self.losing_trades_count
        win_rate = round((self.winning_trades_count / total_trades * 100.0), 1) if total_trades > 0 else 0.0

        return {
            "mode": self.mode,
            "balance": round(self.paper_balance, 2),
            "equity": round(equity, 2),
            "unrealized_pnl": round(unrealized, 2),
            "realized_pnl": round(self.paper_realized_pnl, 2),
            "win_rate": win_rate,
            "total_trades": total_trades,
            "winning_trades": self.winning_trades_count,
            "losing_trades": self.losing_trades_count,
            "profit_factor": 1.0,
            "open_positions_count": len(self.open_positions),
            "daily_drawdown_limit_hit": risk_manager.daily_drawdown_limit_hit,
            "risk_vetoes_count": ml_engine.vetoed_trades_count
        }

    def place_order(
        self,
        symbol: str,
        direction: str,
        size: float,
        entry_price: float,
        sl: float,
        tp: float,
        strategy_name: str,
        reason: str,
        features_snapshot: Optional[any] = None,
        market_regime: str = "UNKNOWN",
        confidence: float = 0.5
    ) -> Optional[Dict]:
        """
        Executes order through fail-closed execution pipeline:
        1. Checks macroeconomic event blackout.
        2. Evaluates 9 deterministic risk gates.
        3. Dispatches to ExecutionService.
        4. If broker execution succeeds, returns confirmed position.
        5. If broker execution fails/uncertain, returns None (NEVER creates ghost position).
        """
        # 1. Macroeconomic Event Blackout Gate
        blackout, blackout_reason = news_feed.is_macro_blackout_active(symbol)
        if blackout:
            print(f"[ExecutionEngine] 🚫 Order VETOED: {blackout_reason}")
            return None

        # 2. Instrument spec
        spec = execution_service.adapter.get_symbol_info(symbol)

        # 3. Deterministic Pre-Trade Risk Gates
        risk_result = risk_manager.evaluate_pre_trade_gates(
            symbol=symbol,
            side=direction,
            entry_price=entry_price,
            sl_price=sl,
            spec=spec,
            open_positions=self.open_positions,
            broker_connected=execution_service.adapter.is_connected()
        )
        if not risk_result.approved:
            print(f"[ExecutionEngine] 🚫 Risk Gate VETO: {risk_result.rejection_reason}")
            return None

        # 4. Dispatch Order through ExecutionService
        client_order_id = f"ord_{uuid.uuid4().hex[:12]}"
        req = OrderRequest(
            client_order_id=client_order_id,
            symbol=symbol,
            side=direction,
            quantity=risk_result.recommended_size or size,
            intended_price=entry_price,
            sl=sl,
            tp=tp,
            strategy=strategy_name,
            market_regime=market_regime
        )

        result = execution_service.submit_order(req)

        # 5. Evaluate Broker Result (Strict Fail-Closed)
        if not result.success or result.status != OrderStatus.FILLED:
            print(f"[ExecutionEngine] ❌ Broker execution failed ({result.status.value}): {result.error_message}")
            return None

        # Reload confirmed positions from DB
        self.open_positions = execution_service.get_open_positions()

        # Find matching newly confirmed position
        confirmed_pos = next((p for p in self.open_positions if p["order_id"] == client_order_id or p.get("broker_order_id") == result.broker_order_id), None)
        if not confirmed_pos and self.open_positions:
            confirmed_pos = self.open_positions[-1]

        print(f"[ExecutionEngine] 🚀 [{self.mode.upper()}] Confirmed {direction} on {symbol} @ {result.executed_price} | Size: {result.executed_quantity}")
        return confirmed_pos

    def close_position(self, position_id: str, exit_reason: str = "MANUAL") -> Optional[Dict]:
        """Closes active position via execution service."""
        target_pos = next((p for p in self.open_positions if p["id"] == position_id), None)
        if not target_pos:
            return None

        close_result = execution_service.close_position(position_id, exit_reason=exit_reason)
        if close_result.success:
            self.open_positions = execution_service.get_open_positions()
            self._load_persisted_state()
            return target_pos
        return None

    def close_all_positions(self, reason: str = "EMERGENCY_STOP") -> int:
        """Emergency liquidation of all open positions."""
        closed_count = 0
        for pos in list(self.open_positions):
            res = self.close_position(pos["id"], exit_reason=reason)
            if res:
                closed_count += 1
        return closed_count

    def update_positions_and_check_exits(self, current_ticks: Dict[str, dict]) -> List[str]:
        """
        Evaluates open positions against incoming ticks.
        Closes on SL, TP, or Trailing Stop breaches.
        """
        closed_ids = []
        for pos in list(self.open_positions):
            symbol = pos["symbol"]
            tick = current_ticks.get(symbol)
            if not tick:
                continue

            current_price = float(tick["price"])
            pos["current_price"] = round(current_price, 4)

            pnl, ret_pct = calculate_trade_pnl(symbol, pos["direction"], float(pos["entry_price"]), current_price, float(pos["size"]))
            pos["unrealized_pnl"] = pnl
            pos["return_pct"] = ret_pct

            # Update SL with Trailing Stop if enabled
            atr_est = abs(float(pos["entry_price"]) - float(pos["sl"])) / max(settings.STOP_LOSS_ATR_MULT, 1.0)
            new_sl = risk_manager.evaluate_trailing_stop(
                pos["direction"],
                float(pos["entry_price"]),
                current_price,
                float(pos["sl"]),
                atr_est
            )
            if new_sl:
                pos["sl"] = new_sl

            # Check SL and TP
            sl_hit = False
            tp_hit = False
            sl_val = float(pos["sl"])
            tp_val = float(pos["tp"])

            if pos["direction"] == "BUY":
                if current_price <= sl_val:
                    sl_hit = True
                elif current_price >= tp_val:
                    tp_hit = True
            elif pos["direction"] == "SELL":
                if current_price >= sl_val:
                    sl_hit = True
                elif current_price <= tp_val:
                    tp_hit = True

            if sl_hit or tp_hit:
                reason = "STOP_LOSS" if sl_hit else "TAKE_PROFIT"
                self.close_position(pos["id"], exit_reason=reason)
                closed_ids.append(pos["id"])

        return closed_ids

execution_engine = ExecutionEngine()
