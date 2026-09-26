import pytest
import uuid
from bot.execution.service import execution_service
from bot.execution.models import OrderRequest, OrderStatus, ExecutionMode
from bot.execution.order_state import order_state_machine
from bot.risk.circuit_breakers import circuit_breaker_manager
from bot.risk.risk_manager import risk_manager
from bot.storage.db import db
from bot.security.models import Role, User
from bot.security.auth import generate_access_token
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_invariant_duplicate_client_order_id_prevents_duplicate_execution():
    """Property 8: duplicate client order ID => no duplicate execution (idempotency)."""
    cid = f"idem_{uuid.uuid4().hex[:10]}"
    req = OrderRequest(
        client_order_id=cid,
        symbol="EURUSD",
        side="BUY",
        quantity=0.01,
        intended_price=1.0850
    )

    # First submission
    res1 = execution_service.submit_order(req)
    assert res1.success is True

    # Second submission with IDENTICAL client order ID
    res2 = execution_service.submit_order(req)
    assert res2.client_order_id == cid

    # Verify orders table contains EXACTLY ONE record for this client_order_id
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM orders WHERE client_order_id = ?", (cid,))
    count = cursor.fetchone()["count"]
    conn.close()
    assert count == 1

def test_invariant_state_survives_restart():
    """Property 9: restart => state survives."""
    # Ensure at least 1 position exists
    cid = f"survive_{uuid.uuid4().hex[:10]}"
    req = OrderRequest(
        client_order_id=cid,
        symbol="EURUSD",
        side="BUY",
        quantity=0.05,
        intended_price=1.0850
    )
    execution_service.submit_order(req)

    # Emulate application restart by querying DB directly
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM active_positions")
    count_before = cursor.fetchone()["count"]
    conn.close()

    assert count_before > 0

    # New service instance simulates reboot
    from bot.execution.service import ExecutionService
    fresh_service = ExecutionService(mode=ExecutionMode.PAPER)
    loaded_positions = fresh_service.get_open_positions()

    assert len(loaded_positions) == count_before

def test_invariant_unauthorized_user_cannot_invoke_privileged_actions(viewer_token):
    """Property 2: unauthorized user => no privileged action."""
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Attempting emergency stop
    resp1 = client.post("/api/emergency-stop", headers=headers)
    assert resp1.status_code == 403

    # Attempting manual order
    resp2 = client.post("/api/trade/manual", json={"direction": "BUY"}, headers=headers)
    assert resp2.status_code == 403

    # Attempting account reset
    resp3 = client.post("/api/account/reset", headers=headers)
    assert resp3.status_code == 403
