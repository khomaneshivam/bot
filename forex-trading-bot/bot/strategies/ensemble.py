import numpy as np
import pandas as pd
from typing import Dict, Tuple, List, Optional
from bot.ai.ml_engine import ml_engine
from bot.ai.correlation_engine import correlation_engine
from bot.ai.agent import gemini_agent
from bot.config.settings import settings
from bot.risk.psychology_guard import psychology_guard
from bot.data.news_feed import news_feed_engine

class StrategyEnsemble:
    def __init__(self):
        # Base strategy performance weights
        self.strategy_weights = {
            "Trend_Momentum": 1.1,
            "Mean_Reversion": 1.0,
            "Volatility_Breakout": 1.0,
            "Smart_Money_SMC": 1.1,
            "Correlation_Macro": 1.3,   # Institutional Macro & DXY Divergence Strategy
            "AI_Deep_Predictor": 1.2
        }
        self.strategy_stats = {
            name: {"wins": 0, "losses": 0, "total_pnl": 0.0} 
            for name in self.strategy_weights
        }
        self.last_consensus_reason = ""

    def evaluate_trend_momentum(self, row: pd.Series, prev: pd.Series) -> Tuple[str, float]:
        """Triple EMA + MACD acceleration + ADX trend strength."""
        adx = row.get("adx", 20.0)
        dist_ema9 = row.get("dist_ema_9", 0.0)
        dist_ema21 = row.get("dist_ema_21", 0.0)
        dist_ema50 = row.get("dist_ema_50", 0.0)
        macd_diff = row.get("macd_diff_norm", 0.0)
        prev_macd_diff = prev.get("macd_diff_norm", 0.0)

        # Bullish alignment: 9 > 21 > 50
        bull_align = (dist_ema9 > dist_ema21 > dist_ema50) and (dist_ema50 > -0.01)
        bear_align = (dist_ema9 < dist_ema21 < dist_ema50) and (dist_ema50 < 0.01)

        if bull_align and macd_diff > prev_macd_diff and adx > 22:
            return "BUY", min(0.95, 0.65 + (adx / 100.0))
        elif bear_align and macd_diff < prev_macd_diff and adx > 22:
            return "SELL", min(0.95, 0.65 + (adx / 100.0))
        return "HOLD", 0.0

    def evaluate_mean_reversion(self, row: pd.Series, prev: pd.Series) -> Tuple[str, float]:
        """Bollinger Band extremes + RSI oversold/overbought bounce."""
        rsi = row.get("rsi_14", 50.0)
        bb_pct_b = row.get("bb_pct_b", 0.5)
        stoch_k = row.get("stoch_k", 50.0)
        stoch_d = row.get("stoch_d", 50.0)
        prev_stoch_k = prev.get("stoch_k", 50.0)
        prev_stoch_d = prev.get("stoch_d", 50.0)

        # Oversold bounce: price at lower band, RSI < 32, Stoch K crosses above D
        if (bb_pct_b < 0.08 or rsi < 32) and (stoch_k > stoch_d and prev_stoch_k <= prev_stoch_d):
            conf = 0.70 + (32 - min(rsi, 32)) * 0.01
            return "BUY", min(0.95, conf)

        # Overbought reversal: price at upper band, RSI > 68, Stoch K crosses below D
        if (bb_pct_b > 0.92 or rsi > 68) and (stoch_k < stoch_d and prev_stoch_k >= prev_stoch_d):
            conf = 0.70 + (max(rsi, 68) - 68) * 0.01
            return "SELL", min(0.95, conf)

        return "HOLD", 0.0

    def evaluate_volatility_breakout(self, row: pd.Series, prev: pd.Series) -> Tuple[str, float]:
        """Donchian Channel / ATR channel expansion with volume confirmation."""
        donchian_pct = row.get("donchian_pct", 0.5)
        vol_ratio = row.get("vol_ratio", 1.0)
        atr_ratio = row.get("atr_ratio", 1.0)

        if donchian_pct >= 0.98 and vol_ratio > 1.35 and atr_ratio > 1.1:
            return "BUY", min(0.92, 0.70 + (vol_ratio - 1.0) * 0.1)
        elif donchian_pct <= 0.02 and vol_ratio > 1.35 and atr_ratio > 1.1:
            return "SELL", min(0.92, 0.70 + (vol_ratio - 1.0) * 0.1)
        return "HOLD", 0.0

    def evaluate_smart_money(self, df: pd.DataFrame) -> Tuple[str, float]:
        """
        20+ Years Hedge Fund Smart Money Concepts (SMC):
        1. Turtle Soup Liquidity Sweeps (trapping breakout retail traders)
        2. Fair Value Gap (FVG) Imbalance retests
        3. Premium vs Discount equilibrium zone qualification
        """
        if len(df) < 5:
            return "HOLD", 0.0

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        c3 = df.iloc[-3]
        recent_low = df["low"].iloc[-15:-2].min()
        recent_high = df["high"].iloc[-15:-2].max()
        range_high = df["high"].iloc[-30:].max()
        range_low = df["low"].iloc[-30:].min()
        equilibrium = (range_high + range_low) / 2.0 if range_high > range_low else curr["close"]

        # 1. Bullish Liquidity Sweep at Discount (< equilibrium)
        if prev["low"] < recent_low and curr["close"] > recent_low and curr["is_bull_candle"] == 1.0:
            if curr.get("lower_shadow_ratio", 0.0) > 0.35 and curr["close"] <= equilibrium * 1.01:
                return "BUY", 0.89

        # Bearish Liquidity Sweep at Premium (> equilibrium)
        if prev["high"] > recent_high and curr["close"] < recent_high and curr["is_bull_candle"] == 0.0:
            if curr.get("upper_shadow_ratio", 0.0) > 0.35 and curr["close"] >= equilibrium * 0.99:
                return "SELL", 0.89

        # 2. Institutional Fair Value Gap (FVG) Imbalance Retest
        # Bullish 3-candle FVG: candle[i-2] High is strictly lower than candle[i] Low (liquidity void)
        if curr["low"] > c3["high"] and curr["is_bull_candle"] == 1.0:
            return "BUY", 0.84
        elif curr["high"] < c3["low"] and curr["is_bull_candle"] == 0.0:
            return "SELL", 0.84

        return "HOLD", 0.0

    def evaluate_correlation_macro(self, symbol: str, row: pd.Series) -> Tuple[str, float]:
        """
        Institutional Macro Correlation Strategy:
        Exploits lead-lag relationships between synthetic DXY Dollar Index and target pair.
        """
        clean = symbol.upper().replace("-", "").replace("/", "")
        dxy_trend = correlation_engine.dxy_trend
        dxy_val = correlation_engine.dxy_current_value

        is_usd_counter = clean in ["EURUSD", "GBPUSD", "AUDUSD", "XAUUSD"]
        is_usd_base = clean in ["USDJPY", "USDCHF", "USDCAD"]

        # Inverse pair check: EURUSD vs USDCHF
        if clean == "EURUSD":
            corr = correlation_engine.get_pair_correlation("EURUSD", "USDCHF")
            if dxy_trend == "BEARISH_CONTRACTION" and row.get("rsi_14", 50) < 65:
                return "BUY", 0.86
            elif dxy_trend == "BULLISH_EXPANSION" and row.get("rsi_14", 50) > 35:
                return "SELL", 0.86

        # Gold vs USD Divergence
        if clean == "XAUUSD":
            if dxy_trend == "BEARISH_CONTRACTION" and row.get("dist_ema_21", 0.0) > -0.005:
                return "BUY", 0.88
            elif dxy_trend == "BULLISH_EXPANSION" and row.get("dist_ema_21", 0.0) < 0.005:
                return "SELL", 0.88

        # General USD counter
        if is_usd_counter:
            if dxy_trend == "BEARISH_CONTRACTION":
                return "BUY", 0.80
            elif dxy_trend == "BULLISH_EXPANSION":
                return "SELL", 0.80

        # General USD base
        if is_usd_base:
            if dxy_trend == "BULLISH_EXPANSION":
                return "BUY", 0.80
            elif dxy_trend == "BEARISH_CONTRACTION":
                return "SELL", 0.80

        return "HOLD", 0.0

    def get_regime_weights(self, regime: str) -> Dict[str, float]:
        """Dynamically adjusts strategy multipliers based on active market regime."""
        if "STRONG_BULL" in regime or "STRONG_BEAR" in regime:
            return {
                "Trend_Momentum": 1.6,
                "Volatility_Breakout": 1.3,
                "Mean_Reversion": 0.4,
                "Smart_Money_SMC": 1.1,
                "Correlation_Macro": 1.4,
                "AI_Deep_Predictor": 1.3
            }
        elif "RANGING" in regime or "CHOP" in regime:
            return {
                "Trend_Momentum": 0.4,
                "Volatility_Breakout": 0.4,
                "Mean_Reversion": 1.7,
                "Smart_Money_SMC": 1.4,
                "Correlation_Macro": 1.2,
                "AI_Deep_Predictor": 1.2
            }
        elif "HIGH_VOLATILITY" in regime:
            return {
                "Trend_Momentum": 1.2,
                "Volatility_Breakout": 1.8,
                "Mean_Reversion": 0.5,
                "Smart_Money_SMC": 1.2,
                "Correlation_Macro": 1.5,
                "AI_Deep_Predictor": 1.3
            }
        elif "COMPRESSION" in regime:
            return {
                "Trend_Momentum": 0.5,
                "Volatility_Breakout": 1.5,
                "Mean_Reversion": 0.7,
                "Smart_Money_SMC": 1.5,
                "Correlation_Macro": 1.5,
                "AI_Deep_Predictor": 1.1
            }
        else:
            return {
                "Trend_Momentum": 1.0,
                "Volatility_Breakout": 1.0,
                "Mean_Reversion": 1.0,
                "Smart_Money_SMC": 1.0,
                "Correlation_Macro": 1.0,
                "AI_Deep_Predictor": 1.0
            }

    def penalize_strategy_loss(self, strategy_name: str):
        """Reduces weight of the strategy that caused a losing trade."""
        if strategy_name in self.strategy_weights:
            self.strategy_weights[strategy_name] = max(0.4, self.strategy_weights[strategy_name] * 0.85)
            self.strategy_stats[strategy_name]["losses"] += 1
            print(f"[StrategyEnsemble] Strategy '{strategy_name}' weight decayed to {self.strategy_weights[strategy_name]:.2f}")

    def reward_strategy_win(self, strategy_name: str, pnl: float):
        """Boosts weight of a winning strategy."""
        if strategy_name in self.strategy_weights:
            self.strategy_weights[strategy_name] = min(2.5, self.strategy_weights[strategy_name] * 1.10)
            self.strategy_stats[strategy_name]["wins"] += 1
            self.strategy_stats[strategy_name]["total_pnl"] += pnl

    def decide_autonomous_entry(self, symbol: str, df_features: pd.DataFrame) -> Dict:
        """
        Autonomous Decision Engine:
        1. Evaluates all 6 strategies (including Macro Correlation)
        2. Detects market regime
        3. Cross-examines DXY trend
        4. Calculates weighted consensus
        5. Negative Pattern Shield Veto
        6. Generates SL/TP
        """
        if len(df_features) < 10:
            return {"signal": "HOLD", "confidence": 0.0, "reason": "Insufficient data"}

        curr = df_features.iloc[-1]
        prev = df_features.iloc[-2]
        regime = curr.get("regime_label", "NEUTRAL_FLOW")
        regime_mults = self.get_regime_weights(regime)

        # Collect votes from each strategy
        votes = {}

        # 1. Trend Momentum
        if settings.ENABLE_TREND_STRATEGY:
            s_sig, s_conf = self.evaluate_trend_momentum(curr, prev)
            votes["Trend_Momentum"] = {"signal": s_sig, "conf": s_conf}

        # 2. Mean Reversion
        if settings.ENABLE_MEAN_REVERSION:
            s_sig, s_conf = self.evaluate_mean_reversion(curr, prev)
            votes["Mean_Reversion"] = {"signal": s_sig, "conf": s_conf}

        # 3. Volatility Breakout
        if settings.ENABLE_BREAKOUT_STRATEGY:
            s_sig, s_conf = self.evaluate_volatility_breakout(curr, prev)
            votes["Volatility_Breakout"] = {"signal": s_sig, "conf": s_conf}

        # 4. Smart Money SMC
        if settings.ENABLE_SMC_STRATEGY:
            s_sig, s_conf = self.evaluate_smart_money(df_features)
            votes["Smart_Money_SMC"] = {"signal": s_sig, "conf": s_conf}

        # 5. Correlation & Macro Divergence
        s_sig, s_conf = self.evaluate_correlation_macro(symbol, curr)
        votes["Correlation_Macro"] = {"signal": s_sig, "conf": s_conf}

        # 6. AI Deep Predictor
        if settings.ENABLE_AI_PREDICTOR:
            ai_sig, ai_conf = ml_engine.predict_signal(curr)
            votes["AI_Deep_Predictor"] = {"signal": ai_sig, "conf": ai_conf}

        # Calculate Weighted Aggregate Score
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0

        for strat, data in votes.items():
            effective_weight = self.strategy_weights.get(strat, 1.0) * regime_mults.get(strat, 1.0)
            total_weight += effective_weight

            if data["signal"] == "BUY":
                buy_score += data["conf"] * effective_weight
            elif data["signal"] == "SELL":
                sell_score += data["conf"] * effective_weight

        buy_votes = [d for s, d in votes.items() if d["signal"] == "BUY"]
        sell_votes = [d for s, d in votes.items() if d["signal"] == "SELL"]
        best_buy_conf = max([d["conf"] for d in buy_votes], default=0.0)
        best_sell_conf = max([d["conf"] for d in sell_votes], default=0.0)

        candidate_signal = "HOLD"
        candidate_confidence = 0.0
        top_strategy = "None"

        if buy_score > sell_score and (buy_score >= 0.65 or best_buy_conf >= 0.60):
            candidate_signal = "BUY"
            candidate_confidence = round(min(0.95, max(best_buy_conf, buy_score / 2.0)), 2)
            top_strategy = max(
                (s for s, d in votes.items() if d["signal"] == "BUY"),
                key=lambda s: votes[s]["conf"] * self.strategy_weights.get(s, 1.0),
                default="Ensemble"
            )
        elif sell_score > buy_score and (sell_score >= 0.65 or best_sell_conf >= 0.60):
            candidate_signal = "SELL"
            candidate_confidence = round(min(0.95, max(best_sell_conf, sell_score / 2.0)), 2)
            top_strategy = max(
                (s for s, d in votes.items() if d["signal"] == "SELL"),
                key=lambda s: votes[s]["conf"] * self.strategy_weights.get(s, 1.0),
                default="Ensemble"
            )

        if candidate_signal == "HOLD":
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "strategy": "Ensemble",
                "regime": regime,
                "reason": "Market in equilibrium / No multi-strategy consensus",
                "votes": votes
            }

        # NEGATIVE PATTERN SHIELD CHECK: Has the bot lost in this exact pattern before?
        is_vetoed, veto_reason = ml_engine.evaluate_negative_shield(curr, candidate_signal)
        if is_vetoed:
            self.last_consensus_reason = veto_reason
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "strategy": top_strategy,
                "regime": regime,
                "reason": veto_reason,
                "votes": votes,
                "vetoed": True
            }

        # 20+ YEAR TRADER PSYCHOLOGY GUARD: Tilt, revenge trading & FOMO trap veto
        is_psych_vetoed, psych_reason = psychology_guard.evaluate_entry_psychology(symbol, curr, candidate_signal)
        if is_psych_vetoed:
            self.last_consensus_reason = psych_reason
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "strategy": top_strategy,
                "regime": regime,
                "reason": psych_reason,
                "votes": votes,
                "vetoed": True
            }

        # LIVE MACRO & NEWS VOLATILITY SHIELD: Prevent entering right before high-impact spread blowout
        is_news_vetoed, news_reason = news_feed_engine.evaluate_news_volatility_shield(symbol)
        if is_news_vetoed:
            self.last_consensus_reason = news_reason
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "strategy": top_strategy,
                "regime": regime,
                "reason": news_reason,
                "votes": votes,
                "vetoed": True
            }

        # GOOGLE GEMINI NEURAL VALIDATION CHECK
        close = float(curr["close"])
        ctx = {
            "symbol": symbol,
            "price": close,
            "regime": regime,
            "dxy_proxy": correlation_engine.dxy_current_value,
            "dxy_trend": correlation_engine.dxy_trend,
            "rsi": float(curr.get("rsi_14", 50.0)),
            "adx": float(curr.get("adx", 20.0)),
            "ema50": float(curr.get("ema_50", close)),
            "ema200": float(curr.get("ema_200", close)),
            "macd_diff": float(curr.get("macd_diff_norm", 0.0)),
            "strategy_consensus": candidate_signal,
            "wrong_trades_lessons": [wt.get("loss_cause") for wt in ml_engine.wrong_trades[-3:]]
        }
        gem_sig, gem_conf, gem_reason = gemini_agent.get_ai_decision(ctx)
        if gem_sig != "HOLD" and gem_sig != candidate_signal:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "strategy": top_strategy,
                "regime": regime,
                "reason": f"Vetoed by Gemini Analyst: {gem_reason}",
                "votes": votes,
                "vetoed": True
            }

        # Dynamic ATR SL / TP
        close = float(curr["close"])
        atr = float(curr.get("atr_14", close * 0.005))
        if atr <= 0 or np.isnan(atr):
            atr = close * 0.005

        sl_distance = atr * settings.STOP_LOSS_ATR_MULT
        tp_distance = atr * settings.TAKE_PROFIT_ATR_MULT

        if candidate_signal == "BUY":
            sl_price = round(close - sl_distance, 4)
            tp_price = round(close + tp_distance, 4)
        else:
            sl_price = round(close + sl_distance, 4)
            tp_price = round(close - tp_distance, 4)

        dxy_str = f"DXY {correlation_engine.dxy_current_value} ({correlation_engine.dxy_trend})"
        reason = f"{top_strategy} in {regime} [{dxy_str}] with {round(candidate_confidence*100, 1)}% consensus"
        self.last_consensus_reason = reason

        return {
            "signal": candidate_signal,
            "confidence": candidate_confidence,
            "strategy": top_strategy,
            "regime": regime,
            "entry_price": close,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "atr": round(atr, 4),
            "reason": reason,
            "votes": votes,
            "vetoed": False
        }

    def get_strategy_overview(self) -> dict:
        return {
            "weights": self.strategy_weights,
            "stats": self.strategy_stats,
            "last_reason": self.last_consensus_reason
        }

strategy_ensemble = StrategyEnsemble()
