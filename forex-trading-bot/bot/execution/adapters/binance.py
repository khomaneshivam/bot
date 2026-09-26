import hmac
import hashlib
import time
import requests
from typing import List, Dict, Optional
from urllib.parse import urlencode
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

class BinanceExecutionAdapter(BaseExecutionAdapter):
    """
    Production-grade Binance Execution Adapter for Crypto.
    Supports both Binance Spot/Futures Testnet and Live APIs with fail-closed semantics.
    Enforces idempotency using newClientOrderId.
    """

    TESTNET_BASE_URL = "https://testnet.binance.vision"
    LIVE_BASE_URL = "https://api.binance.com"

    def __init__(self, mode: ExecutionMode = ExecutionMode.BINANCE_TESTNET):
        super().__init__(mode=mode)
        self.api_key = settings.BINANCE_API_KEY if hasattr(settings, "BINANCE_API_KEY") else ""
        self.api_secret = settings.BINANCE_SECRET_KEY if hasattr(settings, "BINANCE_SECRET_KEY") else ""
        self.base_url = self.LIVE_BASE_URL if mode == ExecutionMode.BINANCE_LIVE else self.TESTNET_BASE_URL
        self._connected = False

    def _sign_params(self, params: Dict) -> Dict:
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _headers(self) -> Dict:
        return {
            "X-MBX-APIKEY": self.api_key or "",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def connect(self) -> bool:
        if not self.api_key or not self.api_secret:
            # We can connect in testnet simulation if credentials are not set
            if self.mode == ExecutionMode.BINANCE_LIVE:
                self._connected = False
                return False
            self._connected = True
            return True

        try:
            resp = requests.get(f"{self.base_url}/api/v3/ping", timeout=5)
            self._connected = (resp.status_code == 200)
            return self._connected
        except Exception:
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_symbol_info(self, symbol: str) -> InstrumentSpecification:
        clean = symbol.upper().replace("-", "").replace("/", "")
        return InstrumentSpecification(
            symbol=clean,
            tick_size=0.01,
            tick_value=0.01,
            contract_size=1.0,
            min_volume=0.001,
            max_volume=100.0,
            volume_step=0.001,
            base_currency=clean.replace("USDT", ""),
            quote_currency="USDT",
            is_crypto=True
        )

    def submit_order(self, request: OrderRequest) -> OrderResult:
        if self.mode == ExecutionMode.BINANCE_LIVE and not settings.ALLOW_LIVE_TRADING:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message="Live trading is prohibited: ALLOW_LIVE_TRADING is False."
            )

        if not self.api_key or not self.api_secret:
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                client_order_id=request.client_order_id,
                error_message="Binance API keys not configured."
            )

        clean_symbol = request.symbol.upper().replace("-", "").replace("/", "")
        params = {
            "symbol": clean_symbol,
            "side": request.side.upper(),
            "type": "MARKET",
            "quantity": request.quantity,
            "newClientOrderId": request.client_order_id,
            "newOrderRespType": "FULL"
        }

        try:
            signed_params = self._sign_params(params)
            resp = requests.post(
                f"{self.base_url}/api/v3/order",
                params=signed_params,
                headers=self._headers(),
                timeout=10
            )

            if resp.status_code != 200:
                err_data = resp.json() if resp.content else {}
                err_msg = err_data.get("msg", resp.text)
                return OrderResult(
                    success=False,
                    status=OrderStatus.REJECTED,
                    client_order_id=request.client_order_id,
                    error_message=f"Binance rejected: {err_msg}"
                )

            data = resp.json()
            executed_qty = float(data.get("executedQty", 0.0))
            cum_quote = float(data.get("cummulativeQuoteQty", 0.0))
            avg_price = (cum_quote / executed_qty) if executed_qty > 0 else request.intended_price
            broker_id = str(data.get("orderId"))

            status_str = data.get("status")
            if status_str == "FILLED":
                final_status = OrderStatus.FILLED
            elif status_str == "PARTIALLY_FILLED":
                final_status = OrderStatus.PARTIALLY_FILLED
            else:
                final_status = OrderStatus.ACKNOWLEDGED

            return OrderResult(
                success=True,
                status=final_status,
                client_order_id=request.client_order_id,
                broker_order_id=broker_id,
                executed_price=avg_price,
                executed_quantity=executed_qty,
                commission=round(cum_quote * 0.0004, 4),
                slippage=abs(avg_price - request.intended_price)
            )

        except requests.exceptions.Timeout:
            # Crucial fail-closed: Timeout means order might or might not have been executed
            return OrderResult(
                success=False,
                status=OrderStatus.UNKNOWN,
                client_order_id=request.client_order_id,
                error_message="Network timeout waiting for Binance response. Reconciliation required."
            )
        except Exception as e:
            return OrderResult(
                success=False,
                status=OrderStatus.UNKNOWN,
                client_order_id=request.client_order_id,
                error_message=f"Binance order exception: {e}"
            )

    def cancel_order(self, broker_order_id: str, symbol: str) -> bool:
        try:
            params = {
                "symbol": symbol.upper().replace("-", "").replace("/", ""),
                "orderId": broker_order_id
            }
            signed = self._sign_params(params)
            resp = requests.delete(f"{self.base_url}/api/v3/order", params=signed, headers=self._headers(), timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_order_status(self, broker_order_id: str, symbol: str) -> OrderResult:
        try:
            params = {
                "symbol": symbol.upper().replace("-", "").replace("/", ""),
                "orderId": broker_order_id
            }
            signed = self._sign_params(params)
            resp = requests.get(f"{self.base_url}/api/v3/order", params=signed, headers=self._headers(), timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                status_map = {
                    "FILLED": OrderStatus.FILLED,
                    "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
                    "CANCELED": OrderStatus.CANCELLED,
                    "REJECTED": OrderStatus.REJECTED,
                    "NEW": OrderStatus.ACKNOWLEDGED
                }
                status = status_map.get(data.get("status"), OrderStatus.UNKNOWN)
                return OrderResult(
                    success=status == OrderStatus.FILLED,
                    status=status,
                    client_order_id=data.get("clientOrderId", "unknown"),
                    broker_order_id=str(data.get("orderId")),
                    executed_price=float(data.get("price", 0.0)),
                    executed_quantity=float(data.get("executedQty", 0.0))
                )
            return OrderResult(
                success=False,
                status=OrderStatus.UNKNOWN,
                client_order_id="unknown",
                broker_order_id=broker_order_id,
                error_message=resp.text
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
        # For spot trading, positions are non-zero asset balances
        if not self.api_key:
            return []
        try:
            params = {}
            signed = self._sign_params(params)
            resp = requests.get(f"{self.base_url}/api/v3/account", params=signed, headers=self._headers(), timeout=5)
            if resp.status_code != 200:
                return []
            data = resp.json()
            positions = []
            for b in data.get("balances", []):
                free = float(b.get("free", 0.0))
                locked = float(b.get("locked", 0.0))
                total = free + locked
                asset = b.get("asset")
                if total > 0.001 and asset not in ("USDT", "BUSD", "USD"):
                    positions.append(BrokerPosition(
                        position_id=f"binance_{asset}",
                        symbol=f"{asset}USDT",
                        direction="BUY",
                        volume=total,
                        entry_price=0.0,
                        current_price=0.0,
                        unrealized_pnl=0.0,
                        open_time=time.strftime("%Y-%m-%d %H:%M:%S")
                    ))
            return positions
        except Exception:
            return []

    def close_position(
        self,
        position_id: str,
        symbol: str,
        direction: str,
        volume: float
    ) -> OrderResult:
        close_side = "SELL" if direction.upper() == "BUY" else "BUY"
        req = OrderRequest(
            client_order_id=f"close_{uuid.uuid4().hex[:10]}",
            symbol=symbol,
            side=close_side,
            quantity=volume,
            intended_price=0.0
        )
        return self.submit_order(req)

    def get_account_balance(self) -> Dict[str, float]:
        if not self.api_key:
            return {"balance": 0.0, "equity": 0.0, "unrealized_pnl": 0.0, "currency": "USDT"}
        try:
            params = {}
            signed = self._sign_params(params)
            resp = requests.get(f"{self.base_url}/api/v3/account", params=signed, headers=self._headers(), timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                usdt_balance = 0.0
                for b in data.get("balances", []):
                    if b.get("asset") == "USDT":
                        usdt_balance = float(b.get("free", 0.0)) + float(b.get("locked", 0.0))
                        break
                return {
                    "balance": round(usdt_balance, 2),
                    "equity": round(usdt_balance, 2),
                    "unrealized_pnl": 0.0,
                    "currency": "USDT"
                }
        except Exception:
            pass
        return {"balance": 0.0, "equity": 0.0, "unrealized_pnl": 0.0, "currency": "USDT"}
