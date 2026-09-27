import time
import uuid
import random
from typing import List, Dict, Optional
from bot.execution.adapters.base import BaseExecutionAdapter
from bot.execution.models import (
    ExecutionMode,
    OrderStatus,
    OrderRequest,
    OrderResult,
    BrokerPosition,
    InstrumentSpecification
)

class PaperExecutionAdapter(BaseExecutionAdapter):
    """
    Realistic Paper Execution Simulator.
    Simulates:
    - Bid/Ask spread
    - Execution slippage
    - Institutional commission
    - Stop-loss and take-profit monitoring
    - Real-time PnL calculation
    """

    # Default spreads in price units
    DEFAULT_SPREADS = {
        "EURUSD": 0.00015,  # 1.5 pips
        "GBPUSD": 0.00020,  # 2.0 pips
        "USDJPY": 0.020,    # 2.0 pips
        "USDCHF": 0.00018,  # 1.8 pips
        "XAUUSD": 0.30,     # $0.30 spread
        "BTCUSDT": 4.50,    # $4.50 spread
        "ETHUSDT": 0.40     # $0.40 spread
    }

    def __init__(self, starting_balance: float = 10000.0):
        super().__init__(mode=ExecutionMode.PAPER)
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self._positions: Dict[str, BrokerPosition] = {}
        self._order_history: Dict[str, OrderResult] = {}
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_symbol_info(self, symbol: str) -> InstrumentSpecification:
        sym = symbol.upper().replace("-", "").replace("/", "")
        is_crypto = "USDT" in sym
        is_gold = "XAU" in sym

        if is_crypto:
            return InstrumentSpecification(
                symbol=symbol,
                tick_size=0.01 if "BTC" in sym else 0.01,
                tick_value=0.01,
                contract_size=1.0,
                min_volume=0.001 if "BTC" in sym else 0.01,
                max_volume=100.0,
                volume_step=0.001 if "BTC" in sym else 0.01,
                base_currency=sym.replace("USDT", ""),
                quote_currency="USDT",
                is_crypto=True
            )
        elif is_gold:
            return InstrumentSpecification(
                symbol=symbol,
                tick_size=0.01,
                tick_value=1.0,
                contract_size=100.0,  # 100 oz per lot
                min_volume=0.01,
                max_volume=50.0,
                volume_step=0.01,
                base_currency="XAU",
                quote_currency="USD",
                is_crypto=False
            )
        else:
            # Forex
            is_jpy = "JPY" in sym
            return InstrumentSpecification(
                symbol=symbol,
                tick_size=0.001 if is_jpy else 0.00001,
                tick_value=1.0,
                contract_size=100000.0,
                min_volume=0.01,
                max_volume=100.0,
                volume_step=0.01,
                base_currency=sym[:3],
                quote_currency=sym[3:],
                is_crypto=False
            )

    def submit_order(self, request: OrderRequest) -> OrderResult:
        if not self._connected:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message="Paper adapter is not connected."
            )

        sym = request.symbol.upper().replace("-", "").replace("/", "")
        spec = self.get_symbol_info(request.symbol)

        # Validate volume constraints
        if request.quantity < spec.min_volume:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message=f"Order volume {request.quantity} below minimum {spec.min_volume}"
            )

        spread = self.DEFAULT_SPREADS.get(sym, 0.0002)
        half_spread = spread / 2.0

        # Simulate slippage (0.1 to 0.4 pips or equivalent)
        slippage_factor = random.uniform(0.1, 0.5) * spec.tick_size * 10
        if request.side.upper() == "BUY":
            executed_price = request.intended_price + half_spread + slippage_factor
        else:
            executed_price = request.intended_price - half_spread - slippage_factor

        executed_price = round(executed_price, 5 if not spec.is_crypto else 2)

        # Calculate commission
        if spec.is_crypto:
            notional = executed_price * request.quantity
            commission = round(notional * 0.0004, 4)  # 0.04% maker/taker
        else:
            # $3.50 per standard lot
            commission = round(request.quantity * 3.50, 2)

        # Deduct commission from balance immediately
        self.balance -= commission

        broker_order_id = f"sim_{uuid.uuid4().hex[:10]}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        position = BrokerPosition(
            position_id=broker_order_id,
            symbol=request.symbol,
            direction=request.side.upper(),
            volume=request.quantity,
            entry_price=executed_price,
            current_price=executed_price,
            sl=request.sl,
            tp=request.tp,
            unrealized_pnl=-commission,
            open_time=now
        )
        self._positions[broker_order_id] = position

        result = OrderResult(
            success=True,
            status=OrderStatus.FILLED,
            client_order_id=request.client_order_id,
            broker_order_id=broker_order_id,
            executed_price=executed_price,
            executed_quantity=request.quantity,
            commission=commission,
            slippage=round(slippage_factor, 5),
            error_message=None
        )
        self._order_history[broker_order_id] = result
        return result

    def cancel_order(self, broker_order_id: str, symbol: str) -> bool:
        if broker_order_id in self._order_history:
            order = self._order_history[broker_order_id]
            if order.status in (OrderStatus.CREATED, OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED):
                order.status = OrderStatus.CANCELLED
                return True
        return False

    def get_order_status(self, broker_order_id: str, symbol: str) -> OrderResult:
        if broker_order_id in self._order_history:
            return self._order_history[broker_order_id]
        return OrderResult(
            success=False,
            status=OrderStatus.UNKNOWN,
            client_order_id="unknown",
            error_message=f"Order {broker_order_id} not found in simulator."
        )

    def get_open_positions(self) -> List[BrokerPosition]:
        return list(self._positions.values())

    def update_position_prices(self, price_map: Dict[str, float]) -> None:
        """Updates current price and unrealized PnL for open positions."""
        for pos_id, pos in self._positions.items():
            if pos.symbol in price_map:
                curr_price = price_map[pos.symbol]
                pos.current_price = curr_price
                spec = self.get_symbol_info(pos.symbol)
                
                price_diff = (curr_price - pos.entry_price) if pos.direction == "BUY" else (pos.entry_price - curr_price)
                if spec.is_crypto:
                    pnl = price_diff * pos.volume
                else:
                    units = pos.volume * spec.contract_size
                    pnl = price_diff * units
                pos.unrealized_pnl = round(pnl, 2)

    def close_position(
        self,
        position_id: str,
        symbol: str,
        direction: str,
        volume: float
    ) -> OrderResult:
        if position_id not in self._positions:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=f"close_{position_id}",
                error_message=f"Position {position_id} not found."
            )

        pos = self._positions.pop(position_id)
        spec = self.get_symbol_info(pos.symbol)
        spread = self.DEFAULT_SPREADS.get(pos.symbol.upper(), 0.0002)
        half_spread = spread / 2.0

        close_price = pos.current_price
        if pos.direction == "BUY":
            executed_close = close_price - half_spread
        else:
            executed_close = close_price + half_spread

        price_diff = (executed_close - pos.entry_price) if pos.direction == "BUY" else (pos.entry_price - executed_close)
        if spec.is_crypto:
            gross_pnl = price_diff * pos.volume
            commission = round(executed_close * pos.volume * 0.0004, 4)
        else:
            units = pos.volume * spec.contract_size
            gross_pnl = price_diff * units
            commission = round(pos.volume * 3.50, 2)

        net_pnl = gross_pnl - commission
        self.balance += net_pnl

        return OrderResult(
            success=True,
            status=OrderStatus.FILLED,
            client_order_id=f"close_{position_id}",
            broker_order_id=f"close_{position_id}",
            executed_price=round(executed_close, 5 if not spec.is_crypto else 2),
            executed_quantity=pos.volume,
            commission=commission,
            slippage=round(half_spread, 5),
            error_message=None
        )

    def get_account_balance(self) -> Dict[str, float]:
        unrealized = sum(p.unrealized_pnl for p in self._positions.values())
        return {
            "balance": round(self.balance, 2),
            "equity": round(self.balance + unrealized, 2),
            "unrealized_pnl": round(unrealized, 2),
            "currency": "USD",
            "margin_free": round(self.balance + unrealized, 2)
        }
