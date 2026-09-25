import os
import sys
import asyncio

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional

from bot.bot_manager import bot_manager
from bot.execution.engine import execution_engine
from bot.config.settings import settings
from bot.data.market_feed import market_feed
from bot.ai.ml_engine import ml_engine
from bot.ai.audit_scanner import market_audit_scanner
from bot.data.news_feed import news_feed_engine
from bot.risk.psychology_guard import psychology_guard

app = FastAPI(title="QuantAI Autonomous Forex & Crypto Trading Bot")

@app.on_event("startup")
async def startup_event():
    """Initializes portfolio capital to $100 and starts autonomous execution."""
    execution_engine.reset_capital(settings.PAPER_STARTING_BALANCE)
    # Automatically start autonomous loop in paper mode
    asyncio.create_task(bot_manager.start())

# Models for request bodies
class ModeRequest(BaseModel):
    mode: str

class SymbolRequest(BaseModel):
    symbol: str

class ManualTradeRequest(BaseModel):
    direction: str  # "BUY" or "SELL"

class ClosePositionRequest(BaseModel):
    position_id: str

# REST Endpoints
@app.get("/api/status")
async def get_status():
    return bot_manager.get_full_dashboard_state()

@app.post("/api/account/reset")
async def reset_account_capital():
    execution_engine.reset_capital(settings.PAPER_STARTING_BALANCE)
    await bot_manager._broadcast_telemetry()
    return {"status": "success", "balance": execution_engine.paper_balance, "equity": execution_engine.paper_equity}

@app.post("/api/bot/start")
async def start_bot():
    await bot_manager.start()
    return {"status": "success", "message": "Autonomous Bot Started", "is_running": bot_manager.is_running}

@app.post("/api/bot/stop")
async def stop_bot():
    await bot_manager.stop()
    return {"status": "success", "message": "Autonomous Bot Paused", "is_running": bot_manager.is_running}

@app.post("/api/mode")
async def change_mode(req: ModeRequest):
    new_mode = bot_manager.set_mode(req.mode)
    return {"status": "success", "mode": new_mode}

@app.post("/api/symbol")
async def change_symbol(req: SymbolRequest):
    updated_state = await bot_manager.switch_symbol_async(req.symbol)
    return {"status": "success", "symbol": req.symbol, "data": updated_state}

@app.post("/api/retrain")
async def retrain_model():
    result = await bot_manager.trigger_manual_retrain()
    return result

@app.post("/api/trade/manual")
async def manual_trade(req: ManualTradeRequest):
    direction = req.direction.upper()
    if direction not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Invalid direction")
        
    tick = market_feed.get_latest_tick(bot_manager.active_symbol)
    entry_price = float(tick["price"])
    is_crypto = market_feed.is_crypto(bot_manager.active_symbol)
    
    atr = entry_price * 0.005
    sl = entry_price - (atr * 1.5) if direction == "BUY" else entry_price + (atr * 1.5)
    tp = entry_price + (atr * 3.0) if direction == "BUY" else entry_price - (atr * 3.0)
    
    size = 0.01 if is_crypto else 0.05
    order = execution_engine.place_order(
        symbol=bot_manager.active_symbol,
        direction=direction,
        size=size,
        entry_price=entry_price,
        sl=sl,
        tp=tp,
        strategy_name="Manual_Trader",
        reason="Manual user execution from dashboard",
        market_regime="MANUAL"
    )
    if not order:
        return {"status": "error", "message": "Order could not be placed (check open positions or drawdown limits)"}
    
    bot_manager.log_event("SUCCESS", f"Manual {direction} opened on {bot_manager.active_symbol} @ {entry_price:.4f}", "MANUAL_ORDER")
    return {"status": "success", "order": order}

@app.post("/api/position/close")
async def close_position(req: ClosePositionRequest):
    closed = execution_engine.close_position(req.position_id, exit_reason="MANUAL_CLOSE")
    if closed:
        bot_manager.log_event("INFO", f"Closed position #{req.position_id} on {closed['symbol']}", "TRADE_EXEC")
        return {"status": "success", "closed": closed}
    return {"status": "error", "message": "Position not found"}

@app.post("/api/emergency-stop")
async def emergency_stop():
    await bot_manager.stop()
    count = execution_engine.close_all_positions(reason="EMERGENCY_KILL_SWITCH")
    bot_manager.log_event("WARNING", f"🚨 EMERGENCY KILL SWITCH TRIGGERED: Bot halted and {count} positions liquidated!", "EMERGENCY")
    return {"status": "success", "closed_count": count}

@app.get("/api/trades/all")
async def get_all_trades():
    """Returns exhaustive list of all open and closed trades from persistent ledger."""
    from bot.execution.trade_ledger import trade_ledger
    return {
        "status": "success",
        "open_positions": execution_engine.open_positions,
        "closed_trades": trade_ledger.get_all_trades(limit=1000),
        "summary": trade_ledger.get_audit_summary(),
        "account": execution_engine.get_account_summary()
    }

@app.get("/api/trade/{trade_id}")
async def get_trade_details(trade_id: str):
    """Fetches full trade record with serialized entry parameters."""
    from bot.execution.trade_ledger import trade_ledger
    for pos in execution_engine.open_positions:
        if pos["id"] == trade_id:
            return {"status": "success", "is_open": True, "trade": pos}
    trade = trade_ledger.get_trade_by_id(trade_id)
    if trade:
        return {"status": "success", "is_open": False, "trade": trade}
    raise HTTPException(status_code=404, detail="Trade record not found")

@app.get("/api/trades/export")
async def export_trades_csv_route():
    """Exports full trade audit ledger as CSV."""
    from bot.execution.trade_ledger import trade_ledger
    csv_data = trade_ledger.export_trades_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=quant_all_trades_ledger.csv"}
    )

@app.get("/api/wrong-trades")
async def get_wrong_trades():
    return {
        "wrong_trades": ml_engine.wrong_trades,
        "vetoed_count": ml_engine.vetoed_trades_count,
        "last_veto_reason": ml_engine.last_veto_reason
    }

@app.get("/api/audit/matrix")
async def get_audit_matrix():
    """Returns the latest 1-minute multi-pair multi-strategy audit matrix."""
    return market_audit_scanner.get_latest_audit()

@app.post("/api/audit/run")
async def trigger_audit_run():
    """Manually triggers a fresh 1-minute multi-pair audit scan."""
    matrix = await market_audit_scanner.run_full_market_audit()
    return matrix

# WebSocket for real-time telemetry stream
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    bot_manager.ws_subscribers.add(websocket)
    # Send initial state immediately
    await websocket.send_json(bot_manager.get_full_dashboard_state())
    try:
        while True:
            # Keep connection open & handle incoming client messages if any
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        bot_manager.ws_subscribers.discard(websocket)
    except Exception:
        bot_manager.ws_subscribers.discard(websocket)

@app.get("/api/news")
async def get_market_news_route():
    """Returns live Gold catalysts, central bank sentiment, and economic releases."""
    return news_feed_engine.get_news_telemetry()

@app.get("/api/psychology")
async def get_psychology_route():
    """Returns 20+ year institutional trader psychological state and tilt shield metrics."""
    return psychology_guard.get_psychology_telemetry(execution_engine.paper_balance)

# Mount Static and Dist Files for Dashboard Frontend
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client", "dist"))
PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client", "public"))

# Mount assets directory from Vite build if present
dist_assets = os.path.join(DIST_DIR, "assets")
if os.path.exists(dist_assets):
    app.mount("/assets", StaticFiles(directory=dist_assets), name="assets")

if os.path.exists(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")

@app.get("/")
async def serve_index():
    dist_index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    public_index = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(public_index):
        return FileResponse(public_index)
    return {"message": "QuantAI Dashboard server running. React build loading..."}
