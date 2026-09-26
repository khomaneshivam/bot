import pytest
import uuid
from bot.execution.models import OrderStatus, OrderRequest
from bot.execution.order_state import order_state_machine

def test_order_creation_and_idempotency():
    cid = f"test_{uuid.uuid4().hex[:8]}"
    req = OrderRequest(
        client_order_id=cid,
        symbol="EURUSD",
        side="BUY",
        quantity=0.05,
        intended_price=1.0850,
        sl=1.0800,
        tp=1.0950
    )

    # 1. Create order
    order = order_state_machine.create_order(req)
    assert order["client_order_id"] == cid
    assert order["status"] == OrderStatus.CREATED.value

    # 2. Idempotent re-submission returns same order record
    order2 = order_state_machine.create_order(req)
    assert order2["id"] == order["id"]
    assert order2["client_order_id"] == cid

def test_legal_order_state_transitions():
    cid = f"test_{uuid.uuid4().hex[:8]}"
    req = OrderRequest(
        client_order_id=cid,
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.01,
        intended_price=80000.0
    )
    order = order_state_machine.create_order(req)
    order_id = order["id"]

    # CREATED -> RISK_APPROVED
    assert order_state_machine.transition(order_id, OrderStatus.RISK_APPROVED, reason="Risk passed")

    # RISK_APPROVED -> SUBMITTED
    assert order_state_machine.transition(order_id, OrderStatus.SUBMITTED, reason="Sent to broker")

    # SUBMITTED -> FILLED
    assert order_state_machine.transition(
        order_id,
        OrderStatus.FILLED,
        reason="Fill confirmed",
        broker_order_id="b_12345",
        executed_price=80005.0
    )

    # Verify updated record
    final_order = order_state_machine.get_order(order_id)
    assert final_order["status"] == OrderStatus.FILLED.value
    assert final_order["broker_order_id"] == "b_12345"
    assert final_order["executed_price"] == 80005.0

def test_illegal_order_state_transition_raises():
    cid = f"test_{uuid.uuid4().hex[:8]}"
    req = OrderRequest(
        client_order_id=cid,
        symbol="EURUSD",
        side="SELL",
        quantity=0.01,
        intended_price=1.0800
    )
    order = order_state_machine.create_order(req)
    order_id = order["id"]

    # Direct jump from CREATED -> FILLED is illegal
    with pytest.raises(ValueError, match="Illegal order state transition"):
        order_state_machine.transition(order_id, OrderStatus.FILLED)
