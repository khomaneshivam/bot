import os
import sys
import tempfile
import pytest

# Ensure repository root and forex-trading-bot are on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bot.storage.db import db
from bot.security.auth import bootstrap_initial_users
from bot.security.models import Role, User
from bot.security.auth import generate_access_token

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Sets up isolated test database for entire test run."""
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.db_path = temp_db
    db._init_database()
    bootstrap_initial_users()

    yield

    try:
        if os.path.exists(temp_db):
            os.remove(temp_db)
    except Exception:
        pass

@pytest.fixture(autouse=True)
def clean_safety_state():
    """Ensures each test starts and ends with clean circuit breakers, risk state, and empty active positions."""
    from bot.risk.circuit_breakers import circuit_breaker_manager
    from bot.risk.risk_manager import risk_manager
    from bot.execution.reconciliation import reconciliation_service

    circuit_breaker_manager.reset_all()
    reconciliation_service.has_active_mismatch = False
    risk_manager.reset_daily_baseline(10000.0)

    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM active_positions")
        cur.execute("DELETE FROM reconciliation_incidents")
        conn.commit()
        conn.close()
    except Exception:
        pass

    yield

    circuit_breaker_manager.reset_all()
    reconciliation_service.has_active_mismatch = False
    risk_manager.reset_daily_baseline(10000.0)

    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM active_positions")
        cur.execute("DELETE FROM reconciliation_incidents")
        conn.commit()
        conn.close()
    except Exception:
        pass

@pytest.fixture
def admin_token():
    user = User(id="usr_admin", username="admin", role=Role.ADMIN, is_active=True)
    return generate_access_token(user)

@pytest.fixture
def trader_token():
    user = User(id="usr_trader", username="trader", role=Role.TRADER, is_active=True)
    return generate_access_token(user)

@pytest.fixture
def viewer_token():
    user = User(id="usr_viewer", username="viewer", role=Role.READ_ONLY, is_active=True)
    return generate_access_token(user)
