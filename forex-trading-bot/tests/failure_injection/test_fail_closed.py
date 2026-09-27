import pytest
import uuid
from unittest.mock import MagicMock
from bot.execution.service import execution_service
from bot.execution.engine import execution_engine
from bot.execution.models import OrderRequest, OrderStatus, OrderResult, ExecutionMode
from bot.risk.circuit_breakers import circuit_breaker_manager
from bot.risk.risk_manager import risk_manager
from bot.execution.reconciliation import reconciliation_service

@pytest.fixture(autouse=True)
def reset_safety_state():
    circuit_breaker_manager.reset_all()
    reconciliation_service.has_active_mismatch = False
    risk_manager.reset_daily_baseline(10000.0)
    yield
    circuit_breaker_manager.reset_all()
    reconciliation_service.has_active_mismatch = False

def test_broker_rejection_does_not_create_internal_position():
    """
    CRITICAL INVARIANT (Phase 8):
    If broker order submission fails/is rejected, DO NOT create an internal confirmed position.
    """
    execution_service.set_execution_mode(ExecutionMode.PAPER)

    # Mock adapter to simulate broker rejection
    mock_adapter = MagicMock()
    mock_adapter.is_connected.return_value = True
    mock_adapter.submit_order.return_value = OrderResult(
        success=False,
        status=OrderStatus.REJECTED,
        client_order_id="rej_123",
        error_message="Broker: Insufficient margin on exchange"
    )
    mock_adapter.get_symbol_info.return_value = execution_service.adapter.get_symbol_info("EURUSD")

    original_adapter = execution_service.adapter
    execution_service.adapter = mock_adapter

    try:
        initial_positions_count = len(execution_service.get_open_positions())

        req = OrderRequest(
            client_order_id=f"fail_ord_{uuid.uuid4().hex[:8]}",
            symbol="EURUSD",
            side="BUY",
            quantity=0.10,
            intended_price=1.0850
        )

        res = execution_service.submit_order(req)

        assert res.success is False
        assert res.status == OrderStatus.REJECTED

        # Verify open positions in DB has NOT increased
        current_positions_count = len(execution_service.get_open_positions())
        assert current_positions_count == initial_positions_count
    finally:
        execution_service.adapter = original_adapter

def test_broker_timeout_enters_reconciliation_without_open_position():
    """
    CRITICAL INVARIANT (Phase 8):
    If broker response is unknown / timed out, status MUST be UNKNOWN/RECONCILIATION_REQUIRED,
    and NO confirmed position may be added.
    """
    mock_adapter = MagicMock()
    mock_adapter.is_connected.return_value = True
    mock_adapter.get_open_positions.return_value = []
    mock_adapter.submit_order.return_value = OrderResult(
        success=False,
        status=OrderStatus.UNKNOWN,
        client_order_id="timeout_123",
        error_message="Socket timeout waiting for ACK"
    )

    original_adapter = execution_service.adapter
    execution_service.adapter = mock_adapter

    try:
        initial_positions_count = len(execution_service.get_open_positions())

        req = OrderRequest(
            client_order_id=f"timeout_ord_{uuid.uuid4().hex[:8]}",
            symbol="EURUSD",
            side="BUY",
            quantity=0.10,
            intended_price=1.0850
        )

        res = execution_service.submit_order(req)

        assert res.status == OrderStatus.UNKNOWN
        current_positions_count = len(execution_service.get_open_positions())
        assert current_positions_count == initial_positions_count
    finally:
        execution_service.adapter = original_adapter

def test_active_reconciliation_mismatch_halts_new_orders():
    """
    CRITICAL INVARIANT:
    When reconciliation mismatch is active, new order execution is strictly halted.
    """
    reconciliation_service.has_active_mismatch = True

    req = OrderRequest(
        client_order_id=f"halt_ord_{uuid.uuid4().hex[:8]}",
        symbol="EURUSD",
        side="BUY",
        quantity=0.01,
        intended_price=1.0850
    )

    res = execution_service.submit_order(req)
    assert res.success is False
    assert res.status == OrderStatus.REJECTED
    assert "reconciliation desync" in res.error_message.lower()

def test_circuit_breaker_halts_new_orders():
    """
    CRITICAL INVARIANT:
    When any circuit breaker is tripped, new order execution is strictly halted.
    """
    circuit_breaker_manager.trip("SYSTEM_PANIC", "High severity alert triggered")

    req = OrderRequest(
        client_order_id=f"cb_ord_{uuid.uuid4().hex[:8]}",
        symbol="EURUSD",
        side="BUY",
        quantity=0.01,
        intended_price=1.0850
    )

    res = execution_service.submit_order(req)
    assert res.success is False
    assert "circuit breaker is TRIPPED" in res.error_message
