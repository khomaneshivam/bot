import asyncio
import sys
import time
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from bot.config.settings import settings
from bot.data.market_feed import market_feed
from bot.ai.features import compute_all_features, extract_features_vector
from bot.ai.ml_engine import ml_engine
from bot.ai.correlation_engine import correlation_engine
from bot.strategies.ensemble import strategy_ensemble
from bot.risk.risk_manager import risk_manager
from bot.execution.engine import execution_engine
from bot.execution.trade_ledger import trade_ledger
from bot.ai.audit_scanner import market_audit_scanner
from bot.data.news_feed import news_feed_engine
from bot.risk.psychology_guard import psychology_guard

class BotManager:
    def __init__(self):
        self.is_running = False
        self.active_symbol = settings.DEFAULT_SYMBOL
        self.active_timeframe = settings.DEFAULT_TIMEFRAME
        self.loop_task: Optional[asyncio.Task] = None
        
        # State Caches
        self.latest_candles_df: Optional[pd.DataFrame] = None
        self.latest_features_df: Optional[pd.DataFrame] = None
        self.latest_decision: Dict = {"signal": "HOLD", "confidence": 0.0, "reason": "Initializing"}
        self.live_logs: List[Dict] = []
        
        # WebSocket clients registry
        self.ws_subscribers = set()
        
        # Preload initial pairs
        self._startup_preload()

    def _startup_preload(self):
        """Pre-warms active asset and major correlation pairs so the terminal is hot from moment 1."""
        print("[BotManager] Pre-warming market feeds and correlation engine...")
        try:
            # Active asset
            df = market_feed.get_candles(self.active_symbol, limit=100)
            self.latest_candles_df = df
            self.latest_features_df = compute_all_features(df)
            ml_engine.train_on_data(df)
            correlation_engine.update_price_series(self.active_symbol, df["close"])

            # Quick seed for key correlation pairs
            for pair in ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "XAUUSD", "BTCUSDT", "ETHUSDT"]:
                if pair != self.active_symbol:
                    try:
                        p_df = market_feed.get_candles(pair, limit=50)
                        if p_df is not None and not p_df.empty:
                            correlation_engine.update_price_series(pair, p_df["close"])
                    except Exception:
                        pass

            correlation_engine.calculate_dxy_proxy()
            correlation_engine.compute_correlation_matrix()
            print("[BotManager] Pre-warming complete. Correlation Matrix & DXY active.")
        except Exception as e:
            print(f"[BotManager] Startup preload note: {e}")

    def log_event(self, level: str, message: str, tag: str = "SYSTEM"):
        """Logs an event and keeps the last 100 logs for the dashboard."""
        event = {
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "tag": tag,
            "message": message
        }
        self.live_logs.insert(0, event)
        if len(self.live_logs) > 100:
            self.live_logs.pop()
        print(f"[{event['time']}] [{tag}] {message}")

    async def initialize_and_train(self):
        """Fetches historical data and trains the neural ensemble."""
        self.log_event("INFO", f"Initializing market feed for {self.active_symbol}...", "DATA")
        try:
            df = await asyncio.to_thread(market_feed.get_candles, self.active_symbol, self.active_timeframe, 150)
            self.latest_candles_df = df
            self.latest_features_df = compute_all_features(df)
            correlation_engine.update_price_series(self.active_symbol, df["close"])
            
            self.log_event("INFO", f"Training AI Model on {len(df)} bars with 60+ parameters...", "AI")
            res = await asyncio.to_thread(ml_engine.train_on_data, df)
            self.log_event("SUCCESS", f"AI Model trained! Accuracy: {res['accuracy']}% | Parameters: {ml_engine.total_parameters}", "AI")
        except Exception as e:
            self.log_event("WARNING", f"Initial data fetch/train warning: {e}", "SYSTEM")

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        settings.AUTONOMOUS_ENABLED = True
        self.log_event("SUCCESS", f"Autonomous Trading Bot STARTED in [{execution_engine.mode.upper()}] mode!", "BOT")
        
        if self.latest_candles_df is None or not ml_engine.is_trained:
            await self.initialize_and_train()
            
        self.loop_task = asyncio.create_task(self._autonomous_cycle_loop())

    async def stop(self):
        self.is_running = False
        settings.AUTONOMOUS_ENABLED = False
        if self.loop_task:
            self.loop_task.cancel()
            self.loop_task = None
        self.log_event("WARNING", "Autonomous Trading Bot PAUSED.", "BOT")

    async def switch_symbol_async(self, new_symbol: str) -> Dict:
        """
        Instant sub-second symbol switch:
        - Updates active symbol
        - Fetches candles in worker thread
        - Computes features & correlation
        - Broadcasts immediately
        """
        clean = new_symbol.upper().replace("-", "").replace("/", "")
        self.active_symbol = clean
        settings.DEFAULT_SYMBOL = clean
        self.log_event("INFO", f"Active asset switched to: {clean}", "CONFIG")

        try:
            df = await asyncio.to_thread(market_feed.get_candles, clean, self.active_timeframe, 100)
            self.latest_candles_df = df
            self.latest_features_df = compute_all_features(df)
            correlation_engine.update_price_series(clean, df["close"])
            self.latest_decision = strategy_ensemble.decide_autonomous_entry(clean, self.latest_features_df)
        except Exception as e:
            self.log_event("ERROR", f"Error loading candles for {clean}: {e}", "DATA")

        await self._broadcast_telemetry()
        return self.get_full_dashboard_state()

    def set_mode(self, new_mode: str) -> str:
        prev_mode = execution_engine.mode
        res = execution_engine.set_mode(new_mode)
        self.log_event("WARNING", f"Trading Mode switched: {prev_mode.upper()} ➔ {res.upper()}", "CONFIG")
        return res

    async def trigger_manual_retrain(self) -> Dict:
        """Manual trigger from the dashboard to re-train the AI model."""
        self.log_event("INFO", "Manual Model Retraining requested...", "AI")
        if self.latest_candles_df is None or self.latest_candles_df.empty:
            try:
                df = await asyncio.to_thread(market_feed.get_candles, self.active_symbol, self.active_timeframe, 150)
                self.latest_candles_df = df
            except Exception as e:
                return {"status": "error", "message": f"Failed to fetch market data: {e}"}

        res = await asyncio.to_thread(ml_engine.train_on_data, self.latest_candles_df)
        self.log_event("SUCCESS", f"AI Model Retrained! Acc: {res['accuracy']}% | Mistakes Fed: {res['wrong_trades_incorporated']}", "AI")
        await self._broadcast_telemetry()
        return res

    async def _autonomous_cycle_loop(self):
        """High-frequency institutional execution loop."""
        while self.is_running:
            try:
                # 1. Fetch live market candles in worker thread for active symbol
                df = await asyncio.to_thread(market_feed.get_candles, self.active_symbol, self.active_timeframe, 150)
                self.latest_candles_df = df
                correlation_engine.update_price_series(self.active_symbol, df["close"])
                
                # 2. Compute 60+ parameters & detect market regime
                df_features = compute_all_features(df)
                self.latest_features_df = df_features
                last_row = df_features.iloc[-1]
                active_tick = {
                    "price": float(last_row["close"]),
                    "time": str(last_row["timestamp"])
                }

                # 3. Track live prices for ALL active open positions & evaluate exits (SL/TP/Trailing Stop)
                current_ticks = {self.active_symbol: active_tick}
                for pos in execution_engine.open_positions:
                    p_sym = pos["symbol"]
                    if p_sym not in current_ticks:
                        t = market_feed.get_latest_tick(p_sym)
                        if t and t.get("price"):
                            current_ticks[p_sym] = t
                        else:
                            cached = market_feed._cache.get(p_sym)
                            if cached is not None and not cached.empty:
                                current_ticks[p_sym] = {
                                    "price": float(cached.iloc[-1]["close"]),
                                    "time": str(cached.iloc[-1]["timestamp"])
                                }

                closed_ids = execution_engine.update_positions_and_check_exits(current_ticks)
                if closed_ids:
                    if settings.AUTO_RETRAIN_ON_WRONG_TRADE and ml_engine.wrong_trades:
                        self.log_event("INFO", f"Wrong trade exited ➔ Retraining AI model on mistake pattern ({len(ml_engine.wrong_trades)} learned)...", "AI_LEARN")
                        await asyncio.to_thread(ml_engine.train_on_data, df)
                        self.log_event("SUCCESS", f"AI Model retrained! Negative Shield active with {len(ml_engine.wrong_trades)} learned patterns.", "AI_LEARN")

                # 4. Multi-Pair Autonomous Opportunity Execution via 1-Minute Audit Scanner
                if settings.AUTONOMOUS_ENABLED and not risk_manager.daily_drawdown_limit_hit:
                    open_symbols = [pos["symbol"] for pos in execution_engine.open_positions]

                    # A. Check 1-minute audit scanner for best opportunities across ANY pair
                    if len(execution_engine.open_positions) < settings.MAX_OPEN_POSITIONS:
                        candidates = market_audit_scanner.get_actionable_candidates(open_symbols=open_symbols)
                        for cand in candidates:
                            if len(execution_engine.open_positions) >= settings.MAX_OPEN_POSITIONS:
                                break

                            cand_sym = cand["symbol"]
                            cand_sig = cand["overall_signal"]
                            cand_chance = cand["overall_chance_pct"]
                            cand_entry = cand["entry_price"]
                            cand_sl = cand["sl_price"]
                            cand_tp = cand["tp_price"]
                            cand_strat = cand["top_strategy"]
                            cand_regime = cand["regime"]
                            cand_conf = cand["confidence"]
                            cand_feats = np.array(cand["features_snapshot"], dtype=np.float32) if cand.get("features_snapshot") else None

                            is_crypto = market_feed.is_crypto(cand_sym)
                            equity = execution_engine.paper_equity
                            size = risk_manager.calculate_position_size(equity, cand_entry, cand_sl, is_crypto)

                            if size > 0:
                                order = execution_engine.place_order(
                                    symbol=cand_sym,
                                    direction=cand_sig,
                                    size=size,
                                    entry_price=cand_entry,
                                    sl=cand_sl,
                                    tp=cand_tp,
                                    strategy_name=cand_strat,
                                    reason=f"Audit Opportunity: {cand_chance}% win probability ({cand_strat})",
                                    features_snapshot=cand_feats,
                                    market_regime=cand_regime,
                                    confidence=cand_conf
                                )
                                if order:
                                    open_symbols.append(cand_sym)
                                    self.log_event(
                                        "SUCCESS",
                                        f"🎯 [AUDIT EXECUTION] Entered {cand_sig} on {cand_sym} @ {cand_entry:.4f} | Win Chance: {cand_chance}% | Strategy: {cand_strat}",
                                        "TRADE_EXEC"
                                    )

                    # B. Check active chart symbol consensus
                    if len(execution_engine.open_positions) < settings.MAX_OPEN_POSITIONS and self.active_symbol not in [p["symbol"] for p in execution_engine.open_positions]:
                        decision = strategy_ensemble.decide_autonomous_entry(self.active_symbol, df_features)
                        self.latest_decision = decision
                        
                        if decision.get("vetoed"):
                            self.log_event("WARNING", f"🛡️ ENTRY BLOCKED: {decision['reason']}", "NEGATIVE_SHIELD")
                        elif decision["signal"] in ["BUY", "SELL"]:
                            is_crypto = market_feed.is_crypto(self.active_symbol)
                            equity = execution_engine.paper_equity
                            entry_p = decision["entry_price"]
                            sl_p = decision["sl_price"]
                            
                            size = risk_manager.calculate_position_size(equity, entry_p, sl_p, is_crypto)
                            feat_snapshot = extract_features_vector(last_row)
                            
                            if size > 0:
                                order = execution_engine.place_order(
                                    symbol=self.active_symbol,
                                    direction=decision["signal"],
                                    size=size,
                                    entry_price=entry_p,
                                    sl=sl_p,
                                    tp=decision["tp_price"],
                                    strategy_name=decision["strategy"],
                                    reason=decision["reason"],
                                    features_snapshot=feat_snapshot,
                                    market_regime=decision["regime"],
                                    confidence=decision["confidence"]
                                )
                                if order:
                                    self.log_event(
                                        "SUCCESS",
                                        f"Entered {decision['signal']} on {self.active_symbol} @ {entry_p:.4f} via {decision['strategy']} ({round(decision['confidence']*100, 1)}% conf)",
                                        "TRADE_EXEC"
                                    )

                # 5. Periodic 1-Minute Multi-Pair Multi-Strategy Audit (runs parallel every 60s)
                if time.time() - market_audit_scanner.last_audit_time >= market_audit_scanner.audit_interval or market_audit_scanner.last_audit_time == 0:
                    asyncio.create_task(market_audit_scanner.run_full_market_audit())

                # 6. Broadcast telemetry to all WebSockets
                await self._broadcast_telemetry()

                # Sleep before next cycle
                await asyncio.sleep(settings.AUTONOMOUS_INTERVAL_SEC)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log_event("ERROR", f"Autonomous cycle error: {e}", "SYSTEM")
                await asyncio.sleep(settings.AUTONOMOUS_INTERVAL_SEC)

    async def _broadcast_telemetry(self):
        """Sends live status to all connected dashboard websockets."""
        if not self.ws_subscribers:
            return
            
        data = self.get_full_dashboard_state()
        dead_clients = set()
        
        for ws in list(self.ws_subscribers):
            try:
                await ws.send_json(data)
            except Exception:
                dead_clients.add(ws)
                
        self.ws_subscribers.difference_update(dead_clients)

    def get_full_dashboard_state(self) -> Dict:
        """Assembles institutional dashboard payload with correlation and ledger records."""
        account = execution_engine.get_account_summary()
        ml_stats = ml_engine.get_stats()
        strat_info = strategy_ensemble.get_strategy_overview()
        corr_info = correlation_engine.get_summary()
        
        # Candles for chart
        candles_list = []
        if self.latest_candles_df is not None and not self.latest_candles_df.empty:
            tail_df = self.latest_candles_df.tail(60)
            for _, r in tail_df.iterrows():
                candles_list.append({
                    "time": str(r["timestamp"]),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r["volume"])
                })

        regime = "NEUTRAL"
        if self.latest_features_df is not None and not self.latest_features_df.empty:
            regime = self.latest_features_df.iloc[-1].get("regime_label", "NEUTRAL")

        # Persistent ledger recent trades
        ledger_trades = trade_ledger.get_recent_trades(limit=25)

        return {
            "is_running": self.is_running,
            "symbol": self.active_symbol,
            "timeframe": self.active_timeframe,
            "market_type": "CRYPTO" if market_feed.is_crypto(self.active_symbol) else "FOREX",
            "account": account,
            "regime": regime,
            "correlation": corr_info,
            "latest_decision": self.latest_decision,
            "ml_stats": ml_stats,
            "strategies": strat_info,
            "open_positions": execution_engine.open_positions,
            "closed_trades": ledger_trades,
            "wrong_trades": ml_engine.wrong_trades[-10:],
            "logs": self.live_logs[:30],
            "candles": candles_list,
            "audit_matrix": market_audit_scanner.get_latest_audit(),
            "news": news_feed_engine.get_news_telemetry(),
            "psychology": psychology_guard.get_psychology_telemetry(account.get("balance", 100.0))
        }

bot_manager = BotManager()
