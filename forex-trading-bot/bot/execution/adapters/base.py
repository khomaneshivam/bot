from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from bot.execution.models import (
    OrderRequest,
    OrderResult,
    BrokerPosition,
    InstrumentSpecification,
    ExecutionMode,
    OrderStatus
)

class BaseExecutionAdapter(ABC):
    """
    Broker-independent abstract execution adapter interface.
    All broker implementations (Paper, MT5, Binance) must implement this contract.
    Ensures fail-closed behavior, structured return types, and explicit reconciliation hooks.
    """

    def __init__(self, mode: ExecutionMode):
        self.mode = mode

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the broker or exchange."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Closes broker connection safely."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if broker connection is active and healthy."""
        pass

    @abstractmethod
    def submit_order(self, request: OrderRequest) -> OrderResult:
        """
        Submits an order to the broker.
        MUST fail closed:
        If submission fails, return OrderResult(success=False, status=OrderStatus.REJECTED).
        If submission status is uncertain (timeout, disconnect), return OrderResult(success=False, status=OrderStatus.UNKNOWN).
        """
        pass

    @abstractmethod
    def cancel_order(self, broker_order_id: str, symbol: str) -> bool:
        """Cancels an existing pending order."""
        pass

    @abstractmethod
    def get_order_status(self, broker_order_id: str, symbol: str) -> OrderResult:
        """Fetches latest execution status of an order directly from the broker."""
        pass

    @abstractmethod
    def get_open_positions(self) -> List[BrokerPosition]:
        """Fetches all open positions directly confirmed by the broker."""
        pass

    @abstractmethod
    def close_position(
        self,
        position_id: str,
        symbol: str,
        direction: str,
        volume: float
    ) -> OrderResult:
        """Closes an existing open broker position."""
        pass

    @abstractmethod
    def get_account_balance(self) -> Dict[str, float]:
        """
        Returns account balance and equity:
        {'balance': float, 'equity': float, 'currency': str, 'margin_free': float}
        """
        pass

    @abstractmethod
    def get_symbol_info(self, symbol: str) -> InstrumentSpecification:
        """Returns instrument contract specifications (tick size, contract size, volume limits)."""
        pass
