import pytest
from fastapi.testclient import TestClient
from server.app import app
from bot.storage.db import db

client = TestClient(app)

def test_login_success():
    resp = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "AdminTrading2026!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "ADMIN"

def test_login_invalid_password_returns_401():
    resp = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "WrongPassword!"
    })
    assert resp.status_code == 401

def test_unauthenticated_request_rejected():
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401

def test_unauthenticated_public_read_endpoints_accessible():
    """Telemetry and public trade ledger endpoints are accessible without authentication."""
    resp_status = client.get("/api/status")
    assert resp_status.status_code == 200
    assert "account" in resp_status.json()

    resp = client.get("/api/trades/all")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "open_positions" in data
    assert "closed_trades" in data

    resp_matrix = client.get("/api/audit/matrix")
    assert resp_matrix.status_code == 200

def test_rbac_read_only_viewer_permissions(viewer_token):
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Viewer can access authenticated profile API
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "READ_ONLY"

    # Viewer cannot start or stop bot
    resp = client.post("/api/bot/start", headers=headers)
    assert resp.status_code == 403

    # Viewer cannot switch mode
    resp = client.post("/api/mode", json={"mode": "paper"}, headers=headers)
    assert resp.status_code == 403

def test_rbac_trader_permissions(trader_token):
    headers = {"Authorization": f"Bearer {trader_token}"}

    # Trader can start bot
    resp = client.post("/api/bot/start", headers=headers)
    assert resp.status_code == 200

    # Trader cannot reset account capital
    resp = client.post("/api/account/reset", headers=headers)
    assert resp.status_code == 403

def test_rbac_admin_permissions(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin can change mode
    resp = client.post("/api/mode", json={"mode": "paper"}, headers=headers)
    assert resp.status_code == 200

    # Admin can reset capital
    resp = client.post("/api/account/reset", headers=headers)
    assert resp.status_code == 200

    # Verify audit event was logged in DB
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_events WHERE action = 'ACCOUNT_RESET' ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row["actor_id"] == "usr_admin"

def test_register_trader_success():
    uname = f"trader_{hash(uname := 'test_new_trader') % 100000}"
    resp = client.post("/api/auth/register", json={
        "username": uname,
        "password": "SecureTrader2026!",
        "confirm_password": "SecureTrader2026!",
        "role": "TRADER"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data
    assert data["role"] == "TRADER"
    assert data["username"] == uname

    # Verify newly registered user can query profile with token
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    profile_resp = client.get("/api/auth/me", headers=headers)
    assert profile_resp.status_code == 200
    assert profile_resp.json()["username"] == uname

def test_register_duplicate_username_conflict():
    resp = client.post("/api/auth/register", json={
        "username": "admin",
        "password": "NewPassword2026!",
        "role": "TRADER"
    })
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()

def test_register_weak_password_validation():
    resp = client.post("/api/auth/register", json={
        "username": "weak_pwd_user",
        "password": "short",
        "role": "TRADER"
    })
    assert resp.status_code == 422

    resp2 = client.post("/api/auth/register", json={
        "username": "no_number_user",
        "password": "onlylettersalltheway",
        "role": "TRADER"
    })
    assert resp2.status_code == 422

def test_register_admin_requires_valid_key():
    # Without admin key should fail 403
    resp_fail = client.post("/api/auth/register", json={
        "username": "unauthorized_admin",
        "password": "SuperAdmin2026!",
        "role": "ADMIN",
        "admin_key": "wrong_key"
    })
    assert resp_fail.status_code == 403

    # With correct admin key should succeed 201
    resp_ok = client.post("/api/auth/register", json={
        "username": f"admin_{hash('new_admin') % 100000}",
        "password": "SuperAdmin2026!",
        "role": "ADMIN",
        "admin_key": "AdminKeyTrading2026!"
    })
    assert resp_ok.status_code == 201
    assert resp_ok.json()["role"] == "ADMIN"

def test_logout_revokes_token_session():
    # Login as trader
    resp = client.post("/api/auth/login", json={
        "username": "trader",
        "password": "TraderTrading2026!"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works
    assert client.get("/api/auth/me", headers=headers).status_code == 200

    # Logout
    logout_resp = client.post("/api/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    # Token should now be rejected as revoked
    me_after_logout = client.get("/api/auth/me", headers=headers)
    assert me_after_logout.status_code == 401

def test_change_password_and_verify_new_login():
    # 1. Create a temporary user
    uname = f"pwd_user_{hash('pwd_user_test') % 100000}"
    resp = client.post("/api/auth/register", json={
        "username": uname,
        "password": "InitialPassword2026!",
        "confirm_password": "InitialPassword2026!",
        "role": "TRADER"
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Try change password with wrong old password
    fail_resp = client.post("/api/auth/change-password", headers=headers, json={
        "old_password": "WrongOldPassword!",
        "new_password": "BrandNewPassword2026!",
        "confirm_password": "BrandNewPassword2026!"
    })
    assert fail_resp.status_code == 400

    # 3. Change password successfully
    ok_resp = client.post("/api/auth/change-password", headers=headers, json={
        "old_password": "InitialPassword2026!",
        "new_password": "BrandNewPassword2026!",
        "confirm_password": "BrandNewPassword2026!"
    })
    assert ok_resp.status_code == 200
    assert ok_resp.json()["success"] is True

    # 4. Verify login with old password fails
    login_old = client.post("/api/auth/login", json={
        "username": uname,
        "password": "InitialPassword2026!"
    })
    assert login_old.status_code == 401

    # 5. Verify login with new password succeeds
    login_new = client.post("/api/auth/login", json={
        "username": uname,
        "password": "BrandNewPassword2026!"
    })
    assert login_new.status_code == 200
    assert "access_token" in login_new.json()
