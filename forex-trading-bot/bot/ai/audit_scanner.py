import asyncio
import sys
import time
import pandas as pd
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from typing import Dict, List, Optional
from bot.data.market_feed import market_feed
from bot.ai.features import compute_all_features, extract_features_vector
from bot.ai.ml_engine import ml_engine
from bot.ai.correlation_engine import correlation_engine
from bot.strategies.ensemble import strategy_ensemble
from bot.config.settings import settings

class MarketAuditScanner:
    """
    1-Minute Multi-Pair Multi-Strategy Audit Engine.
    Evaluates every asset across all 6 quantitative strategies every 60 seconds
    and computes the exact probability/chance of entering a trade for each.
    """
    ALL_PAIRS = [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "XAUUSD",
        "BTCUSDT", "ETHUSDT", "SOLUSDT"
    ]

    def __init__(self):
        self.last_audit_matrix: Dict = {}
        self.last_audit_time: float = 0.0
        self.audit_interval: float = 60.0  # 1 minute
        self._is_scanning: bool = False

    def get_seconds_until_next_audit(self) -> int:
        if self.last_audit_time == 0:
            return 0
        elapsed = time.time() - self.last_audit_time
        return max(0, int(self.audit_interval - elapsed))

    def evaluate_pair_strategies(self, symbol: str, df_candles: Optional[pd.DataFrame]) -> Dict:
        """
        Evaluates a single asset across all 6 strategies and calculates trade probabilities.
        """
        if df_candles is None or len(df_candles) < 15:
            return {
                "symbol": symbol,
                "price": 0.0,
                "regime": "NEUTRAL_FLOW",
                "overall_chance_pct": 15,
                "overall_signal": "HOLD",
                "confidence": 0.0,
                "status_text": "⚪ Market in Equilibrium (15%)",
                "badge_class": "badge-dormant",
                "vetoed": False,
                "veto_reason": None,
                "strategies": {
                    "Trend_Momentum": {"signal": "HOLD", "conf": 0.0, "chance_pct": 10},
                    "Mean_Reversion": {"signal": "HOLD", "conf": 0.0, "chance_pct": 15},
                    "Volatility_Breakout": {"signal": "HOLD", "conf": 0.0, "chance_pct": 10},
                    "Smart_Money_SMC": {"signal": "HOLD", "conf": 0.0, "chance_pct": 15},
                    "Correlation_Macro": {"signal": "HOLD", "conf": 0.0, "chance_pct": 15},
                    "AI_Deep_Predictor": {"signal": "HOLD", "conf": 0.0, "chance_pct": 15}
                }
            }

        df_features = compute_all_features(df_candles)
        curr = df_features.iloc[-1]
        prev = df_features.iloc[-2]
        regime = curr.get("regime_label", "NEUTRAL_FLOW")
        regime_mults = strategy_ensemble.get_regime_weights(regime)
        close_price = float(curr["close"])

        # 1. Evaluate all 6 strategies individually
        t_sig, t_conf = strategy_ensemble.evaluate_trend_momentum(curr, prev)
        m_sig, m_conf = strategy_ensemble.evaluate_mean_reversion(curr, prev)
        v_sig, v_conf = strategy_ensemble.evaluate_volatility_breakout(curr, prev)
        s_sig, s_conf = strategy_ensemble.evaluate_smart_money(df_features)
        c_sig, c_conf = strategy_ensemble.evaluate_correlation_macro(symbol, curr)
        
        # AI predictor
        ai_sig, ai_conf = "HOLD", 0.0
        if ml_engine.is_trained:
            try:
                ai_sig, ai_conf = ml_engine.predict_signal(curr)
            except Exception:
                ai_sig, ai_conf = "HOLD", 0.0

        votes = {
            "Trend_Momentum": {"signal": t_sig, "conf": round(t_conf, 2), "chance_pct": int(t_conf * 100) if t_sig != "HOLD" else int(max(10, (1.0 - abs(curr.get("dist_ema_50", 0)*100))*30))},
            "Mean_Reversion": {"signal": m_sig, "conf": round(m_conf, 2), "chance_pct": int(m_conf * 100) if m_sig != "HOLD" else int(abs(curr.get("rsi_14", 50) - 50)*1.4)},
            "Volatility_Breakout": {"signal": v_sig, "conf": round(v_conf, 2), "chance_pct": int(v_conf * 100) if v_sig != "HOLD" else int(curr.get("vol_ratio", 1.0) * 25)},
            "Smart_Money_SMC": {"signal": s_sig, "conf": round(s_conf, 2), "chance_pct": int(s_conf * 100) if s_sig != "HOLD" else 20},
            "Correlation_Macro": {"signal": c_sig, "conf": round(c_conf, 2), "chance_pct": int(c_conf * 100) if c_sig != "HOLD" else 25},
            "AI_Deep_Predictor": {"signal": ai_sig, "conf": round(ai_conf, 2), "chance_pct": int(ai_conf * 100) if ai_sig != "HOLD" else 30}
        }

        # Calculate weighted consensus score
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0

        for strat, data in votes.items():
            eff_w = strategy_ensemble.strategy_weights.get(strat, 1.0) * regime_mults.get(strat, 1.0)
            total_weight += eff_w
            if data["signal"] == "BUY":
                buy_score += data["conf"] * eff_w
            elif data["signal"] == "SELL":
                sell_score += data["conf"] * eff_w

        buy_votes = [d for s, d in votes.items() if d["signal"] == "BUY"]
        sell_votes = [d for s, d in votes.items() if d["signal"] == "SELL"]
        best_buy_conf = max([d["conf"] for d in buy_votes], default=0.0)
        best_sell_conf = max([d["conf"] for d in sell_votes], default=0.0)

        candidate_signal = "HOLD"
        candidate_confidence = 0.0
        overall_chance = 0

        # Consensus triggers when one side leads and has either solid aggregate score (>=0.65) or single high-conviction signal (>=0.60)
        if buy_score > sell_score and (buy_score >= 0.65 or best_buy_conf >= 0.60):
            candidate_signal = "BUY"
            candidate_confidence = round(min(0.95, max(best_buy_conf, buy_score / 2.0)), 2)
            overall_chance = min(96, max(46, int(candidate_confidence * 85 + (len(buy_votes) - 1) * 5)))
        elif sell_score > buy_score and (sell_score >= 0.65 or best_sell_conf >= 0.60):
            candidate_signal = "SELL"
            candidate_confidence = round(min(0.95, max(best_sell_conf, sell_score / 2.0)), 2)
            overall_chance = min(96, max(46, int(candidate_confidence * 85 + (len(sell_votes) - 1) * 5)))
        else:
            candidate_signal = "HOLD"
            raw_top = max(best_buy_conf, best_sell_conf)
            overall_chance = max(12, int(raw_top * 40))

        # Check Negative Pattern Shield
        is_vetoed = False
        veto_reason = None
        if candidate_signal != "HOLD":
            is_vetoed, v_msg = ml_engine.evaluate_negative_shield(curr, candidate_signal)
            if is_vetoed:
                veto_reason = v_msg
                overall_chance = max(5, int(overall_chance * 0.2))

        # Top contributing strategy
        top_strategy = "Ensemble"
        if candidate_signal != "HOLD":
            top_strategy = max(
                (s for s, d in votes.items() if d["signal"] == candidate_signal),
                key=lambda s: votes[s]["conf"] * strategy_ensemble.strategy_weights.get(s, 1.0),
                default="Ensemble"
            )

        # Dynamic ATR-based Stop Loss and Take Profit
        atr = float(curr.get("atr_14", close_price * 0.005))
        if atr <= 0 or np.isnan(atr):
            atr = close_price * 0.005
        sl_dist = atr * settings.STOP_LOSS_ATR_MULT
        tp_dist = atr * settings.TAKE_PROFIT_ATR_MULT

        if candidate_signal == "BUY":
            sl_price = round(close_price - sl_dist, 4)
            tp_price = round(close_price + tp_dist, 4)
        elif candidate_signal == "SELL":
            sl_price = round(close_price + sl_dist, 4)
            tp_price = round(close_price - tp_dist, 4)
        else:
            sl_price = round(close_price * 0.99, 4)
            tp_price = round(close_price * 1.02, 4)

        feat_vec = extract_features_vector(curr)
        feat_snapshot = feat_vec.tolist() if feat_vec is not None else []

        min_chance = getattr(settings, "AUDIT_TRADE_MIN_CHANCE_PCT", 45)
        is_actionable = (candidate_signal in ["BUY", "SELL"]) and (overall_chance >= min_chance) and (not is_vetoed)

        # Status text & badge
        if is_vetoed:
            status_text = f"🛡️ Vetoed: {veto_reason[:32]}..."
            badge_class = "badge-veto"
        elif candidate_signal == "BUY":
            status_text = f"🟢 High BUY Probability ({overall_chance}%)"
            badge_class = "badge-buy"
        elif candidate_signal == "SELL":
            status_text = f"🔴 High SELL Probability ({overall_chance}%)"
            badge_class = "badge-sell"
        elif overall_chance >= 40:
            status_text = f"🟡 Setup Developing ({overall_chance}%)"
            badge_class = "badge-neutral"
        else:
            status_text = f"⚪ Market in Equilibrium ({overall_chance}%)"
            badge_class = "badge-dormant"

        return {
            "symbol": symbol,
            "price": close_price,
            "regime": regime,
            "overall_chance_pct": overall_chance,
            "overall_signal": candidate_signal,
            "confidence": candidate_confidence,
            "status_text": status_text,
            "badge_class": badge_class,
            "vetoed": is_vetoed,
            "veto_reason": veto_reason,
            "strategies": votes,
            "entry_price": close_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "atr": round(atr, 4),
            "top_strategy": top_strategy,
            "features_snapshot": feat_snapshot,
            "is_actionable": is_actionable
        }

    async def run_full_market_audit(self) -> Dict:
        """
        Executes a 1-minute full audit across all 9 supported Forex & Crypto pairs in parallel.
        """
        if self._is_scanning:
            return self.get_latest_audit()

        self._is_scanning = True
        t0 = time.time()

        async def _scan_pair(symbol: str) -> Dict:
            try:
                df = await asyncio.wait_for(
                    asyncio.to_thread(market_feed.get_candles, symbol, "5m", 80),
                    timeout=2.2
                )
                return self.evaluate_pair_strategies(symbol, df)
            except Exception:
                clean = symbol.upper().replace("-", "").replace("/", "")
                cached_df = market_feed._cache.get(clean)
                return self.evaluate_pair_strategies(symbol, cached_df)

        try:
            tasks = [_scan_pair(sym) for sym in self.ALL_PAIRS]
            results = await asyncio.gather(*tasks, return_exceptions=False)
            results.sort(key=lambda x: x.get("overall_chance_pct", 0), reverse=True)

            top_pick = results[0]["symbol"] if results else "None"
            top_chance = results[0]["overall_chance_pct"] if results else 0

            self.last_audit_time = time.time()
            self.last_audit_matrix = {
                "timestamp": time.strftime("%H:%M:%S"),
                "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                "audit_interval_sec": int(self.audit_interval),
                "next_audit_sec": int(self.audit_interval),
                "scan_duration_ms": int((time.time() - t0) * 1000),
                "top_candidate": f"{top_pick} ({top_chance}% chance)",
                "pairs_scanned": len(results),
                "audit_records": results
            }

            print(f"[MarketAuditScanner] [PARALLEL] Fast Audit Complete: Scanned {len(results)} pairs in {self.last_audit_matrix['scan_duration_ms']}ms. Top: {self.last_audit_matrix['top_candidate']}")
            return self.last_audit_matrix
        finally:
            self._is_scanning = False

    def get_latest_audit(self) -> Dict:
        """Returns the most recent audit with updated countdown."""
        if not self.last_audit_matrix:
            return {
                "timestamp": "Not yet run",
                "next_audit_sec": 0,
                "top_candidate": "Initializing...",
                "pairs_scanned": 0,
                "audit_records": []
            }
        
        matrix = dict(self.last_audit_matrix)
        matrix["next_audit_sec"] = self.get_seconds_until_next_audit()
        return matrix

    def get_actionable_candidates(self, open_symbols: List[str] = None) -> List[Dict]:
        """
        Returns all audited pairs meeting specific autonomous entry criteria:
        - Signal is BUY or SELL
        - Winning probability >= AUDIT_TRADE_MIN_CHANCE_PCT
        - Negative Pattern Shield NOT vetoed
        - Symbol not already in active portfolio
        """
        if open_symbols is None:
            open_symbols = []

        if not self.last_audit_matrix or "audit_records" not in self.last_audit_matrix:
            return []

        candidates = []
        min_chance = getattr(settings, "AUDIT_TRADE_MIN_CHANCE_PCT", 45)

        for rec in self.last_audit_matrix["audit_records"]:
            sym = rec.get("symbol")
            if sym in open_symbols:
                continue

            sig = rec.get("overall_signal", "HOLD")
            chance = rec.get("overall_chance_pct", 0)
            vetoed = rec.get("vetoed", False)

            if sig in ["BUY", "SELL"] and chance >= min_chance and not vetoed:
                candidates.append(rec)

        # Sort by highest winning probability first
        candidates.sort(key=lambda x: x.get("overall_chance_pct", 0), reverse=True)
        return candidates

market_audit_scanner = MarketAuditScanner()
