from enum import Enum
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

class ExecutionMode(str, Enum):
    PAPER = "PAPER"
    MT5_DEMO = "MT5_DEMO"
    MT5_LIVE = "MT5_LIVE"
    BINANCE_TESTNET = "BINANCE_TESTNET"
    BINANCE_LIVE = "BINANCE_LIVE"

    def is_live(self) -> bool:
        return self in (ExecutionMode.MT5_LIVE, ExecutionMode.BINANCE_LIVE)

class OrderStatus(str, Enum):
    CREATED = "CREATED"
    RISK_APPROVED = "RISK_APPROVED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"

LEGAL_TRANSITIONS: Dict[OrderStatus, set] = {
    OrderStatus.CREATED: {OrderStatus.RISK_APPROVED, OrderStatus.REJECTED},
    OrderStatus.RISK_APPROVED: {OrderStatus.SUBMITTED, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.SUBMITTED: {
        OrderStatus.ACKNOWLEDGED,
        OrderStatus.FILLED,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.REJECTED,
        OrderStatus.UNKNOWN,
        OrderStatus.RECONCILIATION_REQUIRED
    },
    OrderStatus.ACKNOWLEDGED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
        OrderStatus.RECONCILIATION_REQUIRED
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.RECONCILIATION_REQUIRED
    },
    OrderStatus.FILLED: {OrderStatus.RECONCILIATION_REQUIRED},
    OrderStatus.REJECTED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.EXPIRED: set(),
    OrderStatus.UNKNOWN: {
        OrderStatus.RECONCILIATION_REQUIRED,
        OrderStatus.REJECTED,
        OrderStatus.FILLED,
        OrderStatus.CANCELLED
    },
    OrderStatus.RECONCILIATION_REQUIRED: {
        OrderStatus.FILLED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
        OrderStatus.ACKNOWLEDGED
    }
}

class InstrumentSpecification(BaseModel):
    symbol: str
    tick_size: float = 0.0001
    tick_value: float = 1.0
    contract_size: float = 100000.0  # Standard lot size for forex
    min_volume: float = 0.01
    max_volume: float = 100.0
    volume_step: float = 0.01
    base_currency: str = "EUR"
    quote_currency: str = "USD"
    is_crypto: bool = False

class OrderRequest(BaseModel):
    client_order_id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    order_type: str = "MARKET"
    intended_price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    strategy: str = "Unknown"
    market_regime: str = "UNKNOWN"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OrderResult(BaseModel):
    success: bool
    status: OrderStatus
    client_order_id: str
    broker_order_id: Optional[str] = None
    executed_price: Optional[float] = None
    executed_quantity: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    error_message: Optional[str] = None

class BrokerPosition(BaseModel):
    position_id: str
    symbol: str
    direction: str  # BUY or SELL
    volume: float
    entry_price: float
    current_price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    unrealized_pnl: float = 0.0
    open_time: str
