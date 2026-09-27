import pytest
from bot.storage.db import db, Database, MySQLConnectionPool
from bot.execution.trade_ledger import trade_ledger

def test_trade_ledger_mysql_read_write_parity():
    """Validates that TradeLedger writes and reads directly from the unified database engine."""
    trade_id = "test_trd_001"
    trade_ledger.log_trade_opened(
        trade_id=trade_id,
        symbol="EURUSD",
        direction="BUY",
        size=0.05,
        entry_price=1.0850,
        sl=1.0820,
        tp=1.0900,
        strategy="Trend_Momentum",
        regime="TRENDING_BULL",
        confidence=0.88,
        dxy_val=103.5,
        features=[1.0, 2.0, 3.0]
    )

    # Verify directly via raw db connection
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row["symbol"] == "EURUSD"
    assert row["direction"] == "BUY"
    assert float(row["entry_price"]) == 1.0850
    assert row["status"] == "OPEN"

    # Close the trade
    trade_ledger.log_trade_closed(
        trade_id=trade_id,
        close_price=1.0890,
        pnl=20.0,
        exit_reason="TAKE_PROFIT"
    )

    recent = trade_ledger.get_recent_trades(limit=10)
    assert len(recent) >= 1
    found = next((t for t in recent if t["id"] == trade_id), None)
    assert found is not None
    assert found["status"] == "CLOSED"
    assert float(found["pnl"]) == 20.0
    assert float(found["return_pct"]) > 0

    # Verify audit summary
    summary = trade_ledger.get_audit_summary()
    assert summary["total_trades"] >= 1
    assert summary["wins"] >= 1
    assert summary["net_pnl"] >= 20.0

def test_connection_pool_active_reuse():
    """Validates that MySQL connection pool reuses idle connections across operations."""
    if db.backend != "mysql" or db._pool is None:
        pytest.skip("MySQL connection pool only active in MySQL mode")

    pool = db._pool
    initial_allocated = pool._allocated

    # Checkout and release 5 times sequentially
    for _ in range(5):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as val")
        res = cursor.fetchone()
        assert res["val"] == 1
        conn.close()

    # The pool should not have created 5 separate physical connections
    assert pool._allocated <= initial_allocated + 1

def test_database_fail_closed_on_unreachable_host(monkeypatch):
    """Validates that when MySQL host is unreachable and fallback is false, fail-closed raises ConnectionError."""
    monkeypatch.setenv("ALLOW_SQLITE_FALLBACK", "false")

    bad_db = Database(
        backend="mysql",
        mysql_host="192.0.2.1", # TEST-NET non-routable IP
        mysql_port=3306,
        mysql_user="invalid_user",
        mysql_password="invalid_password",
        mysql_db="nonexistent_db"
    )
    # Re-instantiate pool with fast 0.5s timeout for test speed
    bad_db._pool = MySQLConnectionPool(
        host="192.0.2.1",
        port=3306,
        user="invalid_user",
        password="invalid_password",
        database="nonexistent_db",
        timeout=0.5
    )

    with pytest.raises(ConnectionError) as exc_info:
        bad_db.get_connection()

    assert "Fail-closed policy engaged" in str(exc_info.value)

def test_account_snapshot_recording():
    """Validates persisting equity snapshots into account_snapshots table."""
    db.record_account_snapshot(
        balance=10500.50,
        equity=10620.75,
        unrealized_pnl=120.25,
        realized_pnl=500.50,
        daily_starting_equity=10000.00,
        drawdown_limit_hit=False
    )

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert float(row["balance"]) == 10500.50
    assert float(row["equity"]) == 10620.75
    assert float(row["unrealized_pnl"]) == 120.25
    assert float(row["realized_pnl"]) == 500.50
    assert float(row["daily_starting_equity"]) == 10000.00
    assert int(row["drawdown_limit_hit"]) == 0

def test_midnight_utc_rollover_clears_drawdown_limit():
    """Validates that crossing midnight UTC resets the daily baseline and clears drawdown trip."""
    from bot.risk.risk_manager import risk_manager
    from bot.risk.circuit_breakers import circuit_breaker_manager

    risk_manager.reset_daily_baseline(1000.0)
    risk_manager.update_equity(940.0) # 6% drawdown on 5% limit -> trips
    assert risk_manager.daily_drawdown_limit_hit is True
    assert circuit_breaker_manager.is_tripped() is True

    # Same day should NOT rollover
    rolled_same_day = risk_manager.check_and_rollover_daily_baseline(risk_manager.last_rollover_utc_date)
    assert rolled_same_day is False
    assert risk_manager.daily_drawdown_limit_hit is True

    # Next UTC day SHOULD rollover
    next_day = "2099-01-01"
    rolled_next_day = risk_manager.check_and_rollover_daily_baseline(next_day)
    assert rolled_next_day is True
    assert risk_manager.daily_drawdown_limit_hit is False
    assert risk_manager.daily_starting_equity == 940.0
    assert risk_manager.last_rollover_utc_date == next_day
