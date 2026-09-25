import math
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

# Standard ICE DXY (US Dollar Index) geometric weights for major currencies
# DXY = 50.14348112 * EURUSD^(-0.576) * USDJPY^(0.136) * GBPUSD^(-0.119) * USDCAD^(0.091) * USDSEK^(0.042) * USDCHF^(0.036)
DXY_WEIGHTS = {
    "EURUSD": -0.576,
    "USDJPY": 0.136,
    "GBPUSD": -0.119,
    "USDCAD": 0.091,
    "USDCHF": 0.036
}

class CorrelationEngine:
    def __init__(self):
        # Historical returns cache: { symbol: pd.Series of pct_changes }
        self.returns_cache: Dict[str, pd.Series] = {}
        self.last_prices: Dict[str, float] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self.dxy_proxy_history: List[float] = []
        self.dxy_current_value: float = 104.50
        self.dxy_trend: str = "NEUTRAL"
        self.last_computed_time: float = 0.0

    def update_price_series(self, symbol: str, close_prices: pd.Series):
        """Updates returns history for a symbol to maintain rolling correlation matrix."""
        clean = symbol.upper().replace("-", "").replace("/", "")
        if close_prices is not None and len(close_prices) >= 10:
            returns = close_prices.pct_change().dropna().tail(100)
            self.returns_cache[clean] = returns
            self.last_prices[clean] = float(close_prices.iloc[-1])

    def calculate_dxy_proxy(self) -> float:
        """
        Calculates a real-time synthetic US Dollar Index (DXY) proxy
        using the international geometric currency basket formula.
        """
        # Ensure we have minimum required forex pairs
        eur = self.last_prices.get("EURUSD", 1.0850)
        jpy = self.last_prices.get("USDJPY", 152.00)
        gbp = self.last_prices.get("GBPUSD", 1.2950)
        cad = self.last_prices.get("USDCAD", 1.3850)
        chf = self.last_prices.get("USDCHF", 0.8850)

        try:
            # Standard ICE DXY Geometric Basket formula
            val = 50.14348112 * (
                math.pow(eur, -0.576) *
                math.pow(jpy, 0.136) *
                math.pow(gbp, -0.119) *
                math.pow(cad, 0.091) *
                math.pow(chf, 0.036)
            )
            val = round(val, 2)
            self.dxy_current_value = val
            self.dxy_proxy_history.append(val)
            if len(self.dxy_proxy_history) > 60:
                self.dxy_proxy_history.pop(0)

            # Determine DXY short-term trend
            if len(self.dxy_proxy_history) >= 5:
                delta = self.dxy_proxy_history[-1] - self.dxy_proxy_history[-5]
                if delta > 0.08:
                    self.dxy_trend = "BULLISH_EXPANSION"
                elif delta < -0.08:
                    self.dxy_trend = "BEARISH_CONTRACTION"
                else:
                    self.dxy_trend = "NEUTRAL"

            return val
        except Exception:
            return self.dxy_current_value

    def compute_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Computes rolling Pearson correlation coefficients across all active pairs.
        Returns a nested dictionary { symbolA: { symbolB: correlation_value } }.
        """
        symbols = list(self.returns_cache.keys())
        if len(symbols) < 2:
            return self.correlation_matrix

        # Build aligned returns DataFrame
        df_returns = pd.DataFrame(self.returns_cache).dropna()
        if len(df_returns) < 10:
            return self.correlation_matrix

        corr_df = df_returns.corr(method="pearson").fillna(0.0)
        matrix = {}
        for s1 in symbols:
            matrix[s1] = {}
            for s2 in symbols:
                if s1 in corr_df and s2 in corr_df.index:
                    matrix[s1][s2] = round(float(corr_df.loc[s1, s2]), 2)
                else:
                    matrix[s1][s2] = 1.0 if s1 == s2 else 0.0

        self.correlation_matrix = matrix
        self.last_computed_time = time.time()
        return matrix

    def get_pair_correlation(self, sym_a: str, sym_b: str) -> float:
        """Returns correlation coefficient between two specific assets [-1.0 to +1.0]."""
        a = sym_a.upper().replace("-", "").replace("/", "")
        b = sym_b.upper().replace("-", "").replace("/", "")
        if a == b:
            return 1.0
        return self.correlation_matrix.get(a, {}).get(b, 0.0)

    def evaluate_correlation_guard(
        self,
        candidate_symbol: str,
        candidate_direction: str,
        existing_positions: List[Dict]
    ) -> Tuple[bool, str]:
        """
        CRITICAL REAL-MONEY SAFETY GUARD:
        1. Validates macro USD alignment (e.g. don't buy EURUSD if DXY is strongly bullish).
        2. Detects inverse pair contradictions (e.g. don't buy EURUSD if USDCHF is also bullish).
        3. Prevents correlated portfolio overconcentration (e.g. don't stack 3x USD-short trades).
        """
        clean_sym = candidate_symbol.upper().replace("-", "").replace("/", "")
        dxy_val = self.calculate_dxy_proxy()

        # 1. Macro USD Alignment Filter
        # If trading EURUSD, GBPUSD, AUDUSD, XAUUSD (which are denominated in USD)
        is_usd_counter = clean_sym in ["EURUSD", "GBPUSD", "AUDUSD", "XAUUSD"]
        is_usd_base = clean_sym in ["USDJPY", "USDCHF", "USDCAD"]

        if is_usd_counter:
            if candidate_direction == "BUY" and self.dxy_trend == "BULLISH_EXPANSION":
                return True, f"VETOED by Correlation Engine: Cannot BUY {clean_sym} against surging US Dollar Index (DXY at {dxy_val} in {self.dxy_trend})"
            elif candidate_direction == "SELL" and self.dxy_trend == "BEARISH_CONTRACTION":
                return True, f"VETOED by Correlation Engine: Cannot SELL {clean_sym} while US Dollar Index is dumping (DXY at {dxy_val} in {self.dxy_trend})"

        if is_usd_base:
            if candidate_direction == "BUY" and self.dxy_trend == "BEARISH_CONTRACTION":
                return True, f"VETOED by Correlation Engine: Cannot BUY {clean_sym} (USD Base) while DXY is dropping ({dxy_val})"
            elif candidate_direction == "SELL" and self.dxy_trend == "BULLISH_EXPANSION":
                return True, f"VETOED by Correlation Engine: Cannot SELL {clean_sym} while DXY is rallying ({dxy_val})"

        # 2. Inverse Pair Conflict Check (EURUSD vs USDCHF)
        if clean_sym == "EURUSD":
            chf_corr = self.get_pair_correlation("EURUSD", "USDCHF")
            # If USDCHF is in existing positions, verify opposite direction
            for pos in existing_positions:
                if pos["symbol"] == "USDCHF":
                    # EURUSD and USDCHF should move inversely
                    if pos["direction"] == candidate_direction and chf_corr < -0.6:
                        return True, f"VETOED by Correlation Engine: Contradiction with existing {pos['direction']} position in USDCHF (Corr: {chf_corr})"

        # 3. Portfolio Correlation Overconcentration Limit
        # Count existing positions with positive correlation >= 0.70 with the candidate
        correlated_positions_count = 0
        for pos in existing_positions:
            corr = self.get_pair_correlation(clean_sym, pos["symbol"])
            # If both are same direction and positively correlated, or opposite direction and negatively correlated
            if (pos["direction"] == candidate_direction and corr >= 0.70) or \
               (pos["direction"] != candidate_direction and corr <= -0.70):
                correlated_positions_count += 1

        if correlated_positions_count >= 2:
            return True, f"VETOED by Risk Manager: Portfolio correlation cap reached ({correlated_positions_count} existing positions already exposed to same currency factor)"

        return False, "Clear: Macro and cross-pair correlation confirmed"

    def get_correlation_features(self, symbol: str) -> Dict[str, float]:
        """
        Extracts quantitative correlation features to feed into the ML model and strategies.
        """
        clean = symbol.upper().replace("-", "").replace("/", "")
        dxy = self.calculate_dxy_proxy()

        # Correlation with EURUSD (benchmark forex)
        corr_eur = self.get_pair_correlation(clean, "EURUSD")
        # Correlation with BTC (crypto benchmark)
        corr_btc = self.get_pair_correlation(clean, "BTCUSDT")
        # Correlation with Gold
        corr_gold = self.get_pair_correlation(clean, "XAUUSD")

        dxy_score = 1.0 if self.dxy_trend == "BULLISH_EXPANSION" else (-1.0 if self.dxy_trend == "BEARISH_CONTRACTION" else 0.0)

        return {
            "dxy_proxy": dxy,
            "dxy_trend_score": dxy_score,
            "corr_with_eur": corr_eur,
            "corr_with_btc": corr_btc,
            "corr_with_gold": corr_gold
        }

    def get_summary(self) -> Dict:
        """Returns clean telemetry for the dashboard heatmap."""
        self.calculate_dxy_proxy()
        self.compute_correlation_matrix()
        return {
            "dxy_value": self.dxy_current_value,
            "dxy_trend": self.dxy_trend,
            "pairs_tracked": list(self.returns_cache.keys()),
            "matrix": self.correlation_matrix,
            "last_updated": time.strftime("%H:%M:%S", time.localtime(self.last_computed_time)) if self.last_computed_time else "Just now"
        }

correlation_engine = CorrelationEngine()
