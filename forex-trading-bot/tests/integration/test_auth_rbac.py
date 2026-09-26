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
    resp = client.get("/api/status")
    assert resp.status_code == 401

def test_rbac_read_only_viewer_permissions(viewer_token):
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Viewer can access read API
    resp = client.get("/api/status", headers=headers)
    assert resp.status_code == 200

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
