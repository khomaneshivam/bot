import pytest
import uuid
from bot.execution.service import execution_service
from bot.execution.models import OrderRequest, OrderStatus, ExecutionMode
from bot.storage.db import db

def test_paper_execution_lifecycle_and_persistence():
    execution_service.set_execution_mode(ExecutionMode.PAPER)

    cid = f"test_{uuid.uuid4().hex[:10]}"
    req = OrderRequest(
        client_order_id=cid,
        symbol="EURUSD",
        side="BUY",
        quantity=0.10,
        intended_price=1.0850,
        sl=1.0800,
        tp=1.0950,
        strategy="TestStrategy",
        market_regime="TRENDING_UP"
    )

    # 1. Submit order
    res = execution_service.submit_order(req)
    assert res.success is True
    assert res.status == OrderStatus.FILLED
    assert res.executed_price is not None
    assert res.commission > 0
    assert res.broker_order_id is not None

    # 2. Check active positions in DB
    positions = execution_service.get_open_positions()
    matching = [p for p in positions if p["broker_order_id"] == res.broker_order_id]
    assert len(matching) == 1
    pos = matching[0]
    pos_id = pos["id"]

    # 3. Check trades ledger table
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE id = ?", (pos_id,))
    trade_row = cursor.fetchone()
    conn.close()
    assert trade_row is not None
    assert trade_row["status"] == "OPEN"

    # 4. Close the position
    close_res = execution_service.close_position(pos_id, exit_reason="TEST_CLOSE")
    assert close_res.success is True

    # 5. Verify position removed from active_positions
    remaining = execution_service.get_open_positions()
    assert not any(p["id"] == pos_id for p in remaining)

    # 6. Verify trade row marked CLOSED with PnL
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE id = ?", (pos_id,))
    closed_trade = cursor.fetchone()
    conn.close()
    assert closed_trade["status"] == "CLOSED"
    assert closed_trade["exit_price"] is not None
    assert closed_trade["net_pnl"] is not None
