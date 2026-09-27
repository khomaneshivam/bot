import time
from typing import List, Dict, Optional
from bot.config.settings import settings
from bot.execution.adapters.base import BaseExecutionAdapter
from bot.execution.models import (
    ExecutionMode,
    OrderStatus,
    OrderRequest,
    OrderResult,
    BrokerPosition,
    InstrumentSpecification
)

# Optional MetaTrader5 dependency
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

class MT5ExecutionAdapter(BaseExecutionAdapter):
    """
    Production-grade MetaTrader 5 execution adapter.
    Enforces fail-closed semantics:
    - Never reports success on failed or uncertain orders.
    - Resolves broker-specific symbol suffixes.
    - Synchronizes live broker positions for reconciliation.
    - Prevents orphan or ghost trades.
    """

    def __init__(self, mode: ExecutionMode = ExecutionMode.MT5_DEMO):
        super().__init__(mode=mode)
        self.account_id = settings.MT5_ACCOUNT
        self.password = settings.MT5_PASSWORD
        self.server = settings.MT5_SERVER
        self.magic_number = settings.MT5_MAGIC_NUMBER
        self._connected = False
        self.last_error = ""

    def connect(self) -> bool:
        if not MT5_AVAILABLE:
            self.last_error = "MetaTrader5 Python library is not installed."
            return False

        try:
            if not mt5.initialize():
                err = mt5.last_error()
                self.last_error = f"MT5 initialize failed: {err}"
                return False

            if self.account_id and self.password and self.server and self.server != "*wRlP5Ja":
                authorized = mt5.login(
                    login=int(self.account_id),
                    password=self.password,
                    server=self.server
                )
                if not authorized:
                    err = mt5.last_error()
                    self.last_error = f"MT5 login failed: {err}"
                    return False

            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                self.last_error = "MT5 terminal info is None."
                return False

            self._connected = True
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    def disconnect(self) -> None:
        if MT5_AVAILABLE and self._connected:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self._connected = False

    def is_connected(self) -> bool:
        if not MT5_AVAILABLE or not self._connected:
            return False
        try:
            term = mt5.terminal_info()
            return term is not None and term.connected
        except Exception:
            return False

    def resolve_broker_symbol(self, standard_symbol: str) -> Optional[str]:
        if not self.is_connected() and not self.connect():
            return None

        clean = standard_symbol.upper().replace("/", "").replace("-", "")
        candidates = [clean, f"{clean}m", f"{clean}.pro", f"{clean}.r", f"{clean}_i", f"{clean}micro"]

        for cand in candidates:
            info = mt5.symbol_info(cand)
            if info is not None:
                if not info.visible:
                    mt5.symbol_select(cand, True)
                return cand
        return None

    def get_symbol_info(self, symbol: str) -> InstrumentSpecification:
        default_spec = InstrumentSpecification(
            symbol=symbol,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            min_volume=0.01,
            max_volume=100.0,
            volume_step=0.01,
            base_currency=symbol[:3],
            quote_currency=symbol[3:],
            is_crypto="USDT" in symbol
        )

        if not self.is_connected() and not self.connect():
            return default_spec

        broker_symbol = self.resolve_broker_symbol(symbol)
        if not broker_symbol:
            return default_spec

        info = mt5.symbol_info(broker_symbol)
        if not info:
            return default_spec

        return InstrumentSpecification(
            symbol=symbol,
            tick_size=info.point,
            tick_value=info.trade_tick_value or 1.0,
            contract_size=info.trade_contract_size or 100000.0,
            min_volume=info.volume_min or 0.01,
            max_volume=info.volume_max or 100.0,
            volume_step=info.volume_step or 0.01,
            base_currency=info.currency_base or symbol[:3],
            quote_currency=info.currency_profit or symbol[3:],
            is_crypto="USDT" in symbol or "BTC" in symbol
        )

    def submit_order(self, request: OrderRequest) -> OrderResult:
        if not self.is_connected() and not self.connect():
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message=f"MT5 broker not connected: {self.last_error}"
            )

        broker_sym = self.resolve_broker_symbol(request.symbol)
        if not broker_sym:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message=f"Symbol '{request.symbol}' not available on MT5"
            )

        tick = mt5.symbol_info_tick(broker_sym)
        if not tick:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message=f"Failed to fetch market tick for {broker_sym}"
            )

        direction = request.side.upper()
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if direction == "BUY" else tick.bid

        # Check broker spread
        info = mt5.symbol_info(broker_sym)
        if info and info.spread > 50:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message=f"Spread {info.spread} points exceeds threshold"
            )

        req_dict = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_sym,
            "volume": float(request.quantity),
            "type": order_type,
            "price": price,
            "sl": float(request.sl) if request.sl else 0.0,
            "tp": float(request.tp) if request.tp else 0.0,
            "deviation": 20,
            "magic": self.magic_number,
            "comment": f"QBot-{request.client_order_id[:8]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        try:
            result = mt5.order_send(req_dict)
            if result is None:
                err = mt5.last_error()
                # Status unknown requires reconciliation
                return OrderResult(
                    success=False,
                    status=OrderStatus.UNKNOWN,
                    client_order_id=request.client_order_id,
                    error_message=f"MT5 order_send returned None (uncertain result): {err}"
                )

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=False,
                    status=OrderStatus.REJECTED,
                    client_order_id=request.client_order_id,
                    broker_order_id=str(result.order) if result.order else None,
                    error_message=f"MT5 rejected ({result.retcode}): {result.comment}"
                )

            executed_price = result.price if result.price > 0 else price
            slippage = abs(executed_price - request.intended_price)

            return OrderResult(
                success=True,
                status=OrderStatus.FILLED,
                client_order_id=request.client_order_id,
                broker_order_id=str(result.order),
                executed_price=executed_price,
                executed_quantity=request.quantity,
                commission=0.0,
                slippage=slippage,
                error_message=None
            )
        except Exception as e:
            return OrderResult(
                success=False,
                status=OrderStatus.UNKNOWN,
                client_order_id=request.client_order_id,
                error_message=f"Exception during MT5 order_send: {e}"
            )

    def cancel_order(self, broker_order_id: str, symbol: str) -> bool:
        if not self.is_connected() and not self.connect():
            return False
        try:
            req = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": int(broker_order_id)
            }
            res = mt5.order_send(req)
            return res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
        except Exception:
            return False

    def get_order_status(self, broker_order_id: str, symbol: str) -> OrderResult:
        if not self.is_connected() and not self.connect():
            return OrderResult(
                success=False,
                status=OrderStatus.UNKNOWN,
                client_order_id="unknown",
                broker_order_id=broker_order_id,
                error_message="MT5 not connected"
            )

        try:
            orders = mt5.history_orders_get(ticket=int(broker_order_id))
            if orders and len(orders) > 0:
                ord_info = orders[0]
                status = OrderStatus.FILLED if ord_info.state == mt5.ORDER_STATE_FILLED else OrderStatus.CANCELLED
                return OrderResult(
                    success=status == OrderStatus.FILLED,
                    status=status,
                    client_order_id="unknown",
                    broker_order_id=broker_order_id,
                    executed_price=ord_info.price_current,
                    executed_quantity=ord_info.volume_initial
                )
            return OrderResult(
                success=False,
                status=OrderStatus.UNKNOWN,
                client_order_id="unknown",
                broker_order_id=broker_order_id,
                error_message="Order ticket not found in history"
            )
        except Exception as e:
            return OrderResult(
                success=False,
                status=OrderStatus.UNKNOWN,
                client_order_id="unknown",
                broker_order_id=broker_order_id,
                error_message=str(e)
            )

    def get_open_positions(self) -> List[BrokerPosition]:
        if not self.is_connected() and not self.connect():
            return []

        try:
            positions = mt5.positions_get()
            if positions is None:
                return []

            result = []
            for p in positions:
                direction = "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL"
                result.append(BrokerPosition(
                    position_id=str(p.ticket),
                    symbol=p.symbol,
                    direction=direction,
                    volume=p.volume,
                    entry_price=p.price_open,
                    current_price=p.price_current,
                    sl=p.sl if p.sl > 0 else None,
                    tp=p.tp if p.tp > 0 else None,
                    unrealized_pnl=p.profit,
                    open_time=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(p.time))
                ))
            return result
        except Exception:
            return []

    def close_position(
        self,
        position_id: str,
        symbol: str,
        direction: str,
        volume: float
    ) -> OrderResult:
        if not self.is_connected() and not self.connect():
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=f"close_{position_id}",
                error_message="MT5 not connected"
            )

        try:
            ticket = int(position_id)
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return OrderResult(
                    success=False,
                    status=OrderStatus.REJECTED,
                    client_order_id=f"close_{position_id}",
                    error_message=f"Position #{ticket} not found on MT5"
                )

            pos = positions[0]
            tick = mt5.symbol_info_tick(pos.symbol)
            if not tick:
                return OrderResult(
                    success=False,
                    status=OrderStatus.REJECTED,
                    client_order_id=f"close_{position_id}",
                    error_message="Failed to get tick for close"
                )

            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "price": price,
                "deviation": 20,
                "magic": self.magic_number,
                "comment": "QBot Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            res = mt5.order_send(req)
            if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=True,
                    status=OrderStatus.FILLED,
                    client_order_id=f"close_{position_id}",
                    broker_order_id=str(res.order),
                    executed_price=res.price if res.price > 0 else price,
                    executed_quantity=pos.volume
                )
            else:
                err = res.comment if res else str(mt5.last_error())
                return OrderResult(
                    success=False,
                    status=OrderStatus.REJECTED,
                    client_order_id=f"close_{position_id}",
                    error_message=f"MT5 close failed: {err}"
                )
        except Exception as e:
            return OrderResult(
                success=False,
                status=OrderStatus.UNKNOWN,
                client_order_id=f"close_{position_id}",
                error_message=f"Close exception: {e}"
            )

    def get_account_balance(self) -> Dict[str, float]:
        if not self.is_connected() and not self.connect():
            return {"balance": 0.0, "equity": 0.0, "unrealized_pnl": 0.0, "margin_free": 0.0, "currency": "USD"}
        try:
            acc = mt5.account_info()
            if acc:
                return {
                    "balance": round(acc.balance, 2),
                    "equity": round(acc.equity, 2),
                    "unrealized_pnl": round(acc.equity - acc.balance, 2),
                    "margin_free": round(acc.margin_free, 2),
                    "currency": acc.currency
                }
        except Exception:
            pass
        return {"balance": 0.0, "equity": 0.0, "unrealized_pnl": 0.0, "margin_free": 0.0, "currency": "USD"}
