import os
import time
import json
import uuid
import hmac
import hashlib
import base64
from typing import Optional, Callable
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Security, Depends, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from bot.storage.db import db
from bot.security.models import Role, User

# Security Settings
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "quantai-production-secret-hmac-key-2026-secure-jwt-replacement")
TOKEN_EXPIRY_SECONDS = int(os.getenv("TOKEN_EXPIRY_SECONDS", "43200"))  # 12 hours

security_scheme = HTTPBearer(auto_error=False)
ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Hashes password with Argon2id."""
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verifies Argon2id password hash with fallback."""
    try:
        return ph.verify(hashed, password)
    except (VerifyMismatchError, Exception):
        return False

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)

def generate_access_token(user: User) -> str:
    """Generates an HMAC-SHA256 signed access token."""
    exp = int(time.time()) + TOKEN_EXPIRY_SECONDS
    jti = uuid.uuid4().hex
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
        "exp": exp,
        "jti": jti
    }
    payload_json = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    payload_b64 = _b64_encode(payload_json)

    sig = hmac.new(
        AUTH_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).digest()
    sig_b64 = _b64_encode(sig)

    token = f"{payload_b64}.{sig_b64}"

    # Record active session in storage
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    exp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(exp))
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO active_sessions (token_hash, user_id, role, created_at, expires_at, is_revoked)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (token_hash, user.id, user.role.value, now, exp_str))
    conn.commit()
    conn.close()

    return token

def verify_access_token(token: str) -> Optional[dict]:
    """Verifies cryptographic signature, expiration, and revocation status."""
    if not token or "." not in token:
        return None

    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig = hmac.new(
            AUTH_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(_b64_decode(sig_b64), expected_sig):
            return None

        payload_bytes = _b64_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp", 0) < time.time():
            return None

        # Check revocation in DB
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_revoked FROM active_sessions WHERE token_hash = ?", (token_hash,))
        row = cursor.fetchone()
        conn.close()

        if row and row["is_revoked"] == 1:
            return None

        return payload
    except Exception:
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> User:
    """FastAPI Dependency: Authenticates Bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload["sub"]
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, is_active, created_at, last_login FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or row["is_active"] != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or removed."
        )

    return User(
        id=row["id"],
        username=row["username"],
        role=Role(row["role"]),
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        last_login=row["last_login"]
    )

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> Optional[User]:
    """FastAPI Dependency: Authenticates Bearer token if provided, returning None if unauthenticated."""
    if not credentials or not credentials.credentials:
        return None

    payload = verify_access_token(credentials.credentials)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, is_active, created_at, last_login FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if not row or row["is_active"] != 1:
            return None

        return User(
            id=row["id"],
            username=row["username"],
            role=Role(row["role"]),
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            last_login=row["last_login"]
        )
    except Exception:
        return None

def require_role(min_role: Role) -> Callable:
    """FastAPI Dependency Factory: Enforces RBAC permissions."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.role.can_access(min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires role '{min_role.value}' or higher, but user has '{current_user.role.value}'."
            )
        return current_user
    return role_checker

def bootstrap_initial_users():
    """Initializes default roles (ADMIN, TRADER, READ_ONLY) if users table is empty."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    count = cursor.fetchone()["cnt"]

    if count == 0:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        admin_pass = os.getenv("ADMIN_INITIAL_PASSWORD", "AdminTrading2026!")
        trader_pass = os.getenv("TRADER_INITIAL_PASSWORD", "TraderTrading2026!")
        viewer_pass = os.getenv("VIEWER_INITIAL_PASSWORD", "ViewerTrading2026!")

        users_to_seed = [
            ("usr_admin", "admin", hash_password(admin_pass), Role.ADMIN.value),
            ("usr_trader", "trader", hash_password(trader_pass), Role.TRADER.value),
            ("usr_viewer", "viewer", hash_password(viewer_pass), Role.READ_ONLY.value),
        ]

        for uid, uname, phash, r in users_to_seed:
            cursor.execute("""
                INSERT INTO users (id, username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (uid, uname, phash, r, now))

        conn.commit()
        print("[Auth] Initialized default RBAC users: 'admin', 'trader', 'viewer'")

    conn.close()

# Run bootstrap on module import
bootstrap_initial_users()
