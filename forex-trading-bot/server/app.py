import os
import sys
import asyncio
import time
import re
import uuid
import hashlib

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, Response, status, Security
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional, Dict

from bot.config.settings import settings
from bot.storage.db import db
from bot.security.models import Role, User, LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, ChangePasswordRequest
from bot.security.auth import (
    get_current_user,
    get_optional_user,
    require_role,
    verify_password,
    hash_password,
    generate_access_token,
    verify_access_token,
    security_scheme,
    bootstrap_initial_users
)
from bot.security.audit import audit_logger
from bot.security.headers import SecurityHeadersMiddleware
from bot.observability.metrics import (
    generate_metrics_output,
    update_portfolio_metrics,
    HTTP_REQUESTS_TOTAL
)
from bot.risk.circuit_breakers import circuit_breaker_manager
from bot.execution.service import execution_service
from bot.execution.engine import execution_engine
from bot.execution.trade_ledger import trade_ledger
from bot.bot_manager import bot_manager
from bot.data.market_feed import market_feed
from bot.data.news_feed import news_feed
from bot.ai.ml_engine import ml_engine
from bot.ai.model_registry import model_registry
from bot.ai.audit_scanner import market_audit_scanner
from bot.risk.psychology_guard import psychology_guard
from bot.risk.risk_manager import risk_manager
from bot.execution.reconciliation import reconciliation_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Production-grade startup recovery sequence:
    1. Initialize storage and tables
    2. Bootstrap RBAC default users
    3. Recover active positions and ledger state (NO auto-reset)
    4. Run initial broker reconciliation
    5. Start autonomous cycle loop
    """
    db.initialize_db()
    bootstrap_initial_users()

    # Reconcile state with broker on boot
    report = execution_service.reconcile()
    if not report.is_synchronized:
        circuit_breaker_manager.trip("BOOT_RECONCILIATION_DESYNC", "Broker state mismatch detected on startup")

    # Start autonomous trading loop
    loop_task = asyncio.create_task(bot_manager.start())
    yield
    # Graceful shutdown sequence
    try:
        await bot_manager.stop()
    except Exception:
        pass

app = FastAPI(
    title="QuantAI Autonomous Trading Platform",
    version="2.0.0",
    docs_url="/docs" if not settings.is_production() else None,
    redoc_url="/redoc" if not settings.is_production() else None,
    openapi_url="/openapi.json" if not settings.is_production() else None,
    lifespan=lifespan
)

# Attach Security Headers & CORS Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def metrics_and_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    HTTP_REQUESTS_TOTAL.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=str(response.status_code)
    ).inc()

    return response

# Request Models
class ModeRequest(BaseModel):
    mode: str

class SymbolRequest(BaseModel):
    symbol: str

class ManualTradeRequest(BaseModel):
    direction: str  # "BUY" or "SELL"

class ClosePositionRequest(BaseModel):
    position_id: str

# -------------------------------------------------------------
# AUTHENTICATION & RBAC ENDPOINTS
# -------------------------------------------------------------

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (req.username,))
    row = cursor.fetchone()
    conn.close()

    client_ip = request.client.host if request.client else None

    if not row or not verify_password(req.password, row["password_hash"]):
        audit_logger.log_event(
            actor_id="anonymous",
            action="LOGIN_FAILED",
            target="auth",
            result="FAILURE",
            ip_address=client_ip
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    user = User(
        id=row["id"],
        username=row["username"],
        role=Role(row["role"]),
        is_active=bool(row["is_active"])
    )

    token = generate_access_token(user)

    audit_logger.log_event(
        actor_id=user.id,
        action="LOGIN_SUCCESS",
        target="auth",
        result="SUCCESS",
        ip_address=client_ip
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        username=user.username
    )

@app.get("/api/auth/me")
async def get_current_user_profile(request: Request, user: User = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Count active non-revoked sessions
    active_sessions_count = 1
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM active_sessions WHERE user_id = ? AND is_revoked = 0", (user.id,))
        row = cursor.fetchone()
        if row:
            active_sessions_count = row["cnt"]
        conn.close()
    except Exception:
        pass

    # Authoritative RBAC capability matrix
    permissions = ["READ_TELEMETRY", "VIEW_ORDERS", "VIEW_POSITIONS", "VIEW_RISK"]
    if user.role in (Role.TRADER, Role.ADMIN):
        permissions.extend(["MANAGE_BOT", "EXECUTE_TRADES", "CLOSE_POSITIONS"])
    if user.role == Role.ADMIN:
        permissions.extend(["SWITCH_MODE", "RESET_CAPITAL", "RESET_CIRCUIT_BREAKERS", "PROMOTE_MODELS"])

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role.value,
        "created_at": user.created_at,
        "last_login": user.last_login,
        "is_active": user.is_active,
        "client_ip": client_ip,
        "active_sessions_count": active_sessions_count,
        "permissions": permissions
    }

@app.post("/api/auth/change-password")
async def change_password(
    req: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user)
):
    client_ip = request.client.host if request.client else None

    # 1. Verify current password
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user.id,))
    row = cursor.fetchone()

    if not row or not verify_password(req.old_password, row["password_hash"]):
        conn.close()
        audit_logger.log_event(
            actor_id=user.id,
            action="PASSWORD_CHANGE_FAILED",
            target="auth",
            result="FAILURE",
            ip_address=client_ip
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current passphrase is incorrect.")

    # 2. Validate new password complexity
    if len(req.new_password) < 8:
        conn.close()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="New password must be at least 8 characters long.")
    if not re.search(r"[0-9]", req.new_password) or not re.search(r"[a-zA-Z]", req.new_password):
        conn.close()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="New password must contain at least one letter and at least one number.")

    # 3. Confirm matching
    if req.confirm_password is not None and req.new_password != req.confirm_password:
        conn.close()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="New passphrase and confirmation passphrase do not match.")

    # 4. Hash and update
    new_hashed = hash_password(req.new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hashed, user.id))
    conn.commit()
    conn.close()

    audit_logger.log_event(
        actor_id=user.id,
        action="PASSWORD_CHANGED",
        target=f"user:{user.username}",
        result="SUCCESS",
        ip_address=client_ip
    )

    return {"success": True, "message": "Passphrase updated successfully."}

@app.post("/api/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, request: Request):
    client_ip = request.client.host if request.client else None
    cleaned_username = req.username.strip().lower()

    # 1. Username syntax validation (alphanumeric, underscores, hyphens, 3-32 chars)
    if not re.match(r"^[a-zA-Z0-9_-]{3,32}$", cleaned_username):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username must be 3-32 characters long and contain only letters, numbers, underscores, and hyphens."
        )

    # 2. Password complexity validation
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long."
        )
    if not re.search(r"[0-9]", req.password) or not re.search(r"[a-zA-Z]", req.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one letter and at least one number."
        )

    # 3. Confirm password matching
    if req.confirm_password is not None and req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password and confirmation password do not match."
        )

    # 4. Role Assignment & Authorization Check
    requested_role_str = (req.role or "TRADER").upper()
    if requested_role_str == "ADMIN":
        expected_admin_key = os.getenv("ADMIN_REGISTRATION_KEY", "AdminKeyTrading2026!")
        if not req.admin_key or req.admin_key != expected_admin_key:
            audit_logger.log_event(
                actor_id="anonymous",
                action="UNAUTHORIZED_ADMIN_REGISTRATION_ATTEMPT",
                target=f"user:{cleaned_username}",
                result="BLOCKED",
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing Admin Registration Key for ADMIN role creation."
            )
        assigned_role = Role.ADMIN
    elif requested_role_str in ("TRADER", "READ_ONLY"):
        assigned_role = Role(requested_role_str)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role specified. Supported roles: TRADER, READ_ONLY, ADMIN."
        )

    # 5. Check for duplicate username in database
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (cleaned_username,))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        audit_logger.log_event(
            actor_id="anonymous",
            action="REGISTRATION_CONFLICT",
            target=f"user:{cleaned_username}",
            result="FAILURE",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered. Please select a different username or sign in."
        )

    # 6. Cryptographic user creation
    new_user_id = f"usr_{uuid.uuid4().hex[:12]}"
    hashed_pwd = hash_password(req.password)
    now_ts = time.strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO users (id, username, password_hash, role, is_active, created_at, last_login)
        VALUES (?, ?, ?, ?, 1, ?, ?)
    """, (new_user_id, cleaned_username, hashed_pwd, assigned_role.value, now_ts, now_ts))
    conn.commit()
    conn.close()

    # 7. Issue initial access token
    new_user = User(
        id=new_user_id,
        username=cleaned_username,
        role=assigned_role,
        is_active=True,
        created_at=now_ts,
        last_login=now_ts
    )
    token = generate_access_token(new_user)

    audit_logger.log_event(
        actor_id=new_user_id,
        action="USER_REGISTERED",
        target=f"user:{cleaned_username}",
        result="SUCCESS",
        ip_address=client_ip
    )

    return RegisterResponse(
        success=True,
        message="Account successfully registered and authenticated.",
        access_token=token,
        token_type="Bearer",
        role=new_user.role,
        user_id=new_user.id,
        username=new_user.username
    )

@app.post("/api/auth/logout")
async def logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    user: Optional[User] = Depends(get_optional_user)
):
    client_ip = request.client.host if request.client else None
    if credentials and credentials.credentials:
        token = credentials.credentials
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE active_sessions SET is_revoked = 1 WHERE token_hash = ?", (token_hash,))
            conn.commit()
            conn.close()
        except Exception:
            pass

    audit_logger.log_event(
        actor_id=user.id if user else "anonymous",
        action="LOGOUT",
        target="auth",
        result="SUCCESS",
        ip_address=client_ip
    )
    return {"success": True, "message": "Session successfully terminated."}

# -------------------------------------------------------------
# TELEMETRY & OBSERVABILITY ENDPOINTS
# -------------------------------------------------------------

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    account = execution_engine.get_account_summary()
    update_portfolio_metrics(
        balance=account["balance"],
        equity=account["equity"],
        active_positions=account["open_positions_count"],
        is_tripped=circuit_breaker_manager.is_tripped()
    )
    return Response(content=generate_metrics_output(), media_type="text/plain; version=0.0.4; charset=utf-8")

@app.get("/api/status")
async def get_status(user: Optional[User] = Depends(get_optional_user)):
    return bot_manager.get_full_dashboard_state()

# -------------------------------------------------------------
# TRADING CONTROLS (RBAC ENFORCED)
# -------------------------------------------------------------

@app.post("/api/bot/start")
async def start_bot(user: User = Depends(require_role(Role.TRADER))):
    await bot_manager.start()
    audit_logger.log_event(
        actor_id=user.id,
        action="BOT_START",
        target="bot_manager",
        result="SUCCESS"
    )
    return {"status": "success", "message": "Autonomous Bot Started", "is_running": bot_manager.is_running}

@app.post("/api/bot/stop")
async def stop_bot(user: User = Depends(require_role(Role.TRADER))):
    await bot_manager.stop()
    audit_logger.log_event(
        actor_id=user.id,
        action="BOT_STOP",
        target="bot_manager",
        result="SUCCESS"
    )
    return {"status": "success", "message": "Autonomous Bot Paused", "is_running": bot_manager.is_running}

@app.post("/api/symbol")
async def change_symbol(req: SymbolRequest, user: User = Depends(require_role(Role.TRADER))):
    old_sym = bot_manager.active_symbol
    updated_state = await bot_manager.switch_symbol_async(req.symbol)
    audit_logger.log_event(
        actor_id=user.id,
        action="SYMBOL_SWITCH",
        target="bot_manager",
        old_value=old_sym,
        new_value=req.symbol,
        result="SUCCESS"
    )
    return {"status": "success", "symbol": req.symbol, "data": updated_state}

@app.post("/api/mode")
async def change_mode(req: ModeRequest, user: User = Depends(require_role(Role.ADMIN))):
    old_mode = execution_engine.mode
    new_mode = bot_manager.set_mode(req.mode)
    audit_logger.log_event(
        actor_id=user.id,
        action="MODE_CHANGE",
        target="execution_engine",
        old_value=old_mode,
        new_value=new_mode,
        result="SUCCESS"
    )
    return {"status": "success", "mode": new_mode}

@app.post("/api/trade/manual")
async def manual_trade(req: ManualTradeRequest, user: User = Depends(require_role(Role.TRADER))):
    direction = req.direction.upper()
    if direction not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Invalid direction")

    tick = market_feed.get_latest_tick(bot_manager.active_symbol)
    if not tick:
        raise HTTPException(status_code=503, detail="Market feed offline or stale")

    entry_price = float(tick["price"])
    atr = entry_price * 0.005
    sl = entry_price - (atr * 1.5) if direction == "BUY" else entry_price + (atr * 1.5)
    tp = entry_price + (atr * 3.0) if direction == "BUY" else entry_price - (atr * 3.0)

    spec = execution_service.adapter.get_symbol_info(bot_manager.active_symbol)
    size = spec.min_volume

    order = execution_engine.place_order(
        symbol=bot_manager.active_symbol,
        direction=direction,
        size=size,
        entry_price=entry_price,
        sl=sl,
        tp=tp,
        strategy_name=f"Manual_{user.username}",
        reason="Manual privileged execution from dashboard",
        market_regime="MANUAL"
    )

    if not order:
        audit_logger.log_event(
            actor_id=user.id,
            action="MANUAL_ORDER_REJECTED",
            target=bot_manager.active_symbol,
            result="FAILURE"
        )
        return {"status": "error", "message": "Order rejected by risk engine or broker"}

    audit_logger.log_event(
        actor_id=user.id,
        action="MANUAL_ORDER_FILLED",
        target=bot_manager.active_symbol,
        new_value=f"{direction} {size} @ {entry_price}",
        result="SUCCESS"
    )
    return {"status": "success", "order": order}

@app.post("/api/position/close")
async def close_position(req: ClosePositionRequest, user: User = Depends(require_role(Role.TRADER))):
    closed = execution_engine.close_position(req.position_id, exit_reason="MANUAL_CLOSE")
    if closed:
        audit_logger.log_event(
            actor_id=user.id,
            action="POSITION_CLOSED",
            target=req.position_id,
            result="SUCCESS"
        )
        return {"status": "success", "closed": closed}
    return {"status": "error", "message": "Position not found"}

@app.post("/api/emergency-stop")
async def emergency_stop(user: User = Depends(require_role(Role.TRADER))):
    await bot_manager.stop()
    count = execution_engine.close_all_positions(reason="EMERGENCY_KILL_SWITCH")
    circuit_breaker_manager.trip("EMERGENCY_KILL_SWITCH", f"Manual emergency halt triggered by {user.username}")
    audit_logger.log_event(
        actor_id=user.id,
        action="EMERGENCY_KILL_SWITCH",
        target="portfolio",
        new_value=f"Liquidated {count} positions",
        result="SUCCESS"
    )
    return {"status": "success", "closed_count": count}

@app.post("/api/account/reset")
async def reset_account_capital(user: User = Depends(require_role(Role.ADMIN))):
    old_balance = execution_engine.paper_balance
    execution_engine.reset_capital(settings.PAPER_STARTING_BALANCE)
    await bot_manager._broadcast_telemetry()
    audit_logger.log_event(
        actor_id=user.id,
        action="ACCOUNT_RESET",
        target="account",
        old_value=str(old_balance),
        new_value=str(settings.PAPER_STARTING_BALANCE),
        result="SUCCESS"
    )
    return {"status": "success", "balance": execution_engine.paper_balance, "equity": execution_engine.paper_equity}

@app.post("/api/retrain")
async def retrain_model(user: User = Depends(require_role(Role.ADMIN))):
    result = await bot_manager.trigger_manual_retrain()
    audit_logger.log_event(
        actor_id=user.id,
        action="MODEL_RETRAIN",
        target="ml_engine",
        new_value=str(result),
        result="SUCCESS"
    )
    return result

@app.post("/api/reconcile")
async def trigger_reconciliation(user: User = Depends(require_role(Role.ADMIN))):
    report = execution_service.reconcile()
    audit_logger.log_event(
        actor_id=user.id,
        action="BROKER_RECONCILIATION",
        target="broker",
        result="SUCCESS" if report.is_synchronized else "DISCREPANCY_DETECTED"
    )
    return report.dict()

@app.post("/api/circuit-breakers/reset")
async def reset_circuit_breakers(user: User = Depends(require_role(Role.ADMIN))):
    circuit_breaker_manager.reset_all()
    audit_logger.log_event(
        actor_id=user.id,
        action="CIRCUIT_BREAKER_RESET",
        target="risk_engine",
        result="SUCCESS"
    )
    return {"status": "success", "message": "All circuit breakers reset."}

# -------------------------------------------------------------
# READ-ONLY DATA ENDPOINTS
# -------------------------------------------------------------

@app.get("/api/trades/all")
async def get_all_trades(user: Optional[User] = Depends(get_optional_user)):
    return {
        "status": "success",
        "open_positions": execution_engine.open_positions,
        "closed_trades": trade_ledger.get_all_trades(limit=1000),
        "summary": trade_ledger.get_audit_summary(),
        "account": execution_engine.get_account_summary()
    }

@app.get("/api/trade/{trade_id}")
async def get_trade_details(trade_id: str, user: Optional[User] = Depends(get_optional_user)):
    for pos in execution_engine.open_positions:
        if pos["id"] == trade_id:
            return {"status": "success", "is_open": True, "trade": pos}
    trade = trade_ledger.get_trade_by_id(trade_id)
    if trade:
        return {"status": "success", "is_open": False, "trade": trade}
    raise HTTPException(status_code=404, detail="Trade record not found")

@app.get("/api/trades/export")
async def export_trades_csv_route(user: Optional[User] = Depends(get_optional_user)):
    csv_data = trade_ledger.export_trades_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=quant_all_trades_ledger.csv"}
    )

@app.get("/api/wrong-trades")
async def get_wrong_trades(user: Optional[User] = Depends(get_optional_user)):
    return {
        "wrong_trades": ml_engine.wrong_trades,
        "vetoed_count": ml_engine.vetoed_trades_count,
        "last_veto_reason": ml_engine.last_veto_reason
    }

@app.get("/api/audit/matrix")
async def get_audit_matrix(user: Optional[User] = Depends(get_optional_user)):
    return market_audit_scanner.get_latest_audit()

@app.get("/api/news")
async def get_market_news_route(user: Optional[User] = Depends(get_optional_user)):
    return news_feed.get_news_telemetry()

@app.get("/api/psychology")
async def get_psychology_route(user: Optional[User] = Depends(get_optional_user)):
    return psychology_guard.get_psychology_telemetry(execution_engine.paper_balance)

@app.get("/api/orders")
async def get_orders(user: Optional[User] = Depends(get_optional_user)):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 200")
    orders = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM order_transitions ORDER BY timestamp DESC LIMIT 500")
    transitions = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"status": "success", "orders": orders, "transitions": transitions}

@app.get("/api/reconciliation/status")
async def get_reconciliation_status(user: Optional[User] = Depends(get_optional_user)):
    report = reconciliation_service.last_report
    broker_positions = execution_service.adapter.get_open_positions()
    serialized_broker = []
    for p in broker_positions:
        if hasattr(p, "model_dump"):
            serialized_broker.append(p.model_dump())
        elif hasattr(p, "dict"):
            serialized_broker.append(p.dict())
        else:
            serialized_broker.append(dict(p))
    return {
        "status": "success",
        "has_active_mismatch": reconciliation_service.has_active_mismatch,
        "report": report.dict() if report else None,
        "internal_positions": execution_service.get_open_positions(),
        "broker_positions": serialized_broker
    }

@app.get("/api/risk/status")
async def get_risk_status(user: Optional[User] = Depends(get_optional_user)):
    cb_status = circuit_breaker_manager.get_status()
    blackout, blackout_reason = news_feed.is_macro_blackout_active(bot_manager.active_symbol)
    return {
        "status": "success",
        "circuit_breakers": cb_status.model_dump() if hasattr(cb_status, "model_dump") else cb_status.dict(),
        "daily_starting_equity": risk_manager.daily_starting_equity,
        "current_equity": risk_manager.current_equity,
        "daily_drawdown_limit_hit": risk_manager.daily_drawdown_limit_hit,
        "max_daily_drawdown_pct": risk_manager.max_daily_drawdown_pct,
        "max_risk_per_trade_pct": risk_manager.max_risk_per_trade_pct,
        "max_concurrent_positions": risk_manager.max_concurrent_positions,
        "max_symbol_positions": risk_manager.max_symbol_positions,
        "macro_blackout_active": blackout,
        "macro_blackout_reason": blackout_reason,
        "broker_connected": execution_service.adapter.is_connected(),
        "feed_fresh": market_feed.is_feed_fresh(bot_manager.active_symbol)
    }

@app.get("/api/models")
async def get_models(user: Optional[User] = Depends(get_optional_user)):
    champion = model_registry.get_champion()
    challenger = model_registry.get_challenger()
    all_models = model_registry.get_all_models()
    return {
        "status": "success",
        "champion": champion,
        "challenger": challenger,
        "models": all_models,
        "stats": ml_engine.get_stats()
    }

@app.get("/api/audit/logs")
async def get_audit_logs(limit: int = 150, user: Optional[User] = Depends(get_optional_user)):
    events = audit_logger.get_recent_audits(limit=limit)
    return {"status": "success", "events": events}

@app.get("/api/system/health")
async def get_system_health(user: Optional[User] = Depends(get_optional_user)):
    import platform
    return {
        "status": "healthy" if not circuit_breaker_manager.is_tripped() else "degraded",
        "api": "ONLINE",
        "database": "CONNECTED",
        "broker": "CONNECTED" if execution_service.adapter.is_connected() else "DISCONNECTED",
        "market_feed": "FRESH" if market_feed.is_feed_fresh(bot_manager.active_symbol) else "STALE",
        "news_feed": "ONLINE",
        "ml_engine": "ONLINE" if ml_engine.is_trained else "INITIALIZING",
        "circuit_breaker": "TRIPPED" if circuit_breaker_manager.is_tripped() else "ARMED",
        "reconciliation": "MISMATCH" if reconciliation_service.has_active_mismatch else "SYNCHRONIZED",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# -------------------------------------------------------------
# AUTHENTICATED WEBSOCKET ENDPOINT
# -------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection for live market data and telemetry streaming.
    Supports authenticated sessions and guest telemetry streaming.
    """
    await websocket.accept()

    token = websocket.query_params.get("token")
    user_payload = None

    if token:
        user_payload = verify_access_token(token)

    # Authorized WebSocket subscriber
    bot_manager.ws_subscribers.add(websocket)
    try:
        await websocket.send_json(bot_manager.get_full_dashboard_state())
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("{"):
                try:
                    auth_msg = json.loads(data)
                    if auth_msg.get("type") == "auth" and auth_msg.get("token"):
                        user_payload = verify_access_token(auth_msg["token"])
                        if user_payload:
                            await websocket.send_json({"type": "auth_ok", "role": user_payload.get("role")})
                except Exception:
                    pass
    except WebSocketDisconnect:
        bot_manager.ws_subscribers.discard(websocket)
    except Exception:
        bot_manager.ws_subscribers.discard(websocket)

# -------------------------------------------------------------
# STATIC & DASHBOARD ASSETS
# -------------------------------------------------------------

DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client", "dist"))
PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client", "public"))

dist_assets = os.path.join(DIST_DIR, "assets")
if os.path.exists(dist_assets):
    app.mount("/assets", StaticFiles(directory=dist_assets), name="assets")

if os.path.exists(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")

@app.get("/")
@app.get("/{full_path:path}")
async def serve_index(full_path: str = ""):
    if full_path.startswith("api") or full_path.startswith("metrics"):
        raise HTTPException(status_code=404, detail="Not Found")
    dist_index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    public_index = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(public_index):
        return FileResponse(public_index)
    return {"message": "QuantAI Dashboard server running. React build loading..."}
