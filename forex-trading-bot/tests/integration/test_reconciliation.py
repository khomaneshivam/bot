import pytest
import uuid
import time
from bot.execution.reconciliation import reconciliation_service
from bot.execution.adapters.paper import PaperExecutionAdapter
from bot.execution.models import BrokerPosition
from bot.storage.db import db

def test_reconciliation_synchronized_clean_state():
    adapter = PaperExecutionAdapter()
    report = reconciliation_service.reconcile(adapter)
    assert report.is_synchronized is True
    assert len(report.discrepancies) == 0

def test_reconciliation_detects_unexpected_broker_position():
    adapter = PaperExecutionAdapter()
    # Inject unexpected position into broker simulator
    pos_id = "unexpected_b_1"
    adapter._positions[pos_id] = BrokerPosition(
        position_id=pos_id,
        symbol="EURUSD",
        direction="BUY",
        volume=0.05,
        entry_price=1.0850,
        current_price=1.0850,
        open_time=time.strftime("%Y-%m-%d %H:%M:%S")
    )

    report = reconciliation_service.reconcile(adapter)
    assert report.is_synchronized is False
    assert reconciliation_service.has_active_mismatch is True

    types = [d.discrepancy_type for d in report.discrepancies]
    assert "UNEXPECTED_BROKER_POSITION" in types

    # Check incident was written to DB
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reconciliation_incidents WHERE incident_type = 'UNEXPECTED_BROKER_POSITION'")
    row = cursor.fetchone()
    conn.close()
    assert row is not None

def test_reconciliation_detects_missing_broker_position():
    # Insert internal position in DB that does NOT exist on broker
    conn = db.get_connection()
    cursor = conn.cursor()
    internal_pos_id = f"pos_{uuid.uuid4().hex[:8]}"
    cursor.execute("""
        INSERT INTO active_positions (id, order_id, broker_order_id, symbol, direction, size, entry_price, current_price, open_time, strategy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (internal_pos_id, "ord_fake", "b_non_existent", "GBPUSD", "BUY", 0.05, 1.2950, 1.2950, "2026-09-26 12:00:00", "Test"))
    conn.commit()
    conn.close()

    adapter = PaperExecutionAdapter()  # Empty positions
    report = reconciliation_service.reconcile(adapter)

    assert report.is_synchronized is False
    types = [d.discrepancy_type for d in report.discrepancies]
    assert "MISSING_BROKER_POSITION" in types

    # Cleanup test position
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_positions WHERE id = ?", (internal_pos_id,))
    conn.commit()
    conn.close()
