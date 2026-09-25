import os
import json
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import accuracy_score

from bot.ai.features import compute_all_features, extract_features_vector, FEATURE_COLUMNS
from bot.config.settings import settings

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "wrong_trades_memory.json")

class MLEngine:
    def __init__(self):
        self.scaler = RobustScaler()
        self.model = HistGradientBoostingClassifier(
            max_iter=150,
            learning_rate=0.06,
            max_depth=6,
            min_samples_leaf=15,
            l2_regularization=1.5,
            random_state=42
        )
        self.is_trained = False
        self.total_parameters = len(FEATURE_COLUMNS) * 150 * 6  # Ensemble tree parameter proxy
        self.last_trained_time: Optional[str] = None
        self.training_accuracy: float = 0.0
        self.retrain_count: int = 0
        
        # Wrong Trades Memory & Negative Shield
        self.wrong_trades: List[Dict] = []
        self.wrong_trade_vectors: List[np.ndarray] = []
        self.vetoed_trades_count: int = 0
        self.last_veto_reason: str = ""
        
        self._load_memory()

    def _load_memory(self):
        """Loads persistent memory of past wrong trades."""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    data = json.load(f)
                    self.wrong_trades = data.get("wrong_trades", [])
                    self.vetoed_trades_count = data.get("vetoed_count", 0)
                    self.wrong_trade_vectors = [
                        np.array(t["features_at_entry"], dtype=np.float32) 
                        for t in self.wrong_trades if "features_at_entry" in t
                    ]
            except Exception as e:
                print(f"[MLEngine] Error loading memory file: {e}")

    def _save_memory(self):
        """Saves wrong trades memory to disk."""
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump({
                    "wrong_trades": self.wrong_trades,
                    "vetoed_count": self.vetoed_trades_count,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2)
        except Exception as e:
            print(f"[MLEngine] Error saving memory: {e}")

    def generate_labels(self, df: pd.DataFrame, forward_bars: int = 4, atr_mult: float = 1.0) -> np.ndarray:
        """
        Creates forward-looking target labels:
        1 = Profitable BUY (Price rises > atr_mult * ATR)
        -1 = Profitable SELL (Price falls > atr_mult * ATR)
        0 = HOLD / Chop (No clear breakout)
        """
        close = df["close"].values
        atr = df["atr_14"].values if "atr_14" in df.columns else close * 0.005
        n = len(close)
        labels = np.zeros(n, dtype=int)

        for i in range(n - forward_bars):
            future_max = np.max(close[i+1 : i+1+forward_bars])
            future_min = np.min(close[i+1 : i+1+forward_bars])
            current = close[i]
            target_delta = max(atr[i] * atr_mult, current * 0.002)

            up_move = future_max - current
            down_move = current - future_min

            if up_move > target_delta and up_move > down_move * 1.3:
                labels[i] = 1   # BUY
            elif down_move > target_delta and down_move > up_move * 1.3:
                labels[i] = 2   # SELL (mapped to 2 for 0,1,2 classification)
            else:
                labels[i] = 0   # HOLD

        return labels

    def train_on_data(self, df: pd.DataFrame) -> dict:
        """
        Trains model on large multi-parameter features with sample weighting for mistakes.
        """
        if len(df) < 50:
            return {"status": "error", "message": "Insufficient data"}

        features_df = compute_all_features(df)
        labels = self.generate_labels(features_df)

        # Build feature matrix X
        X_list = []
        for i in range(len(features_df)):
            X_list.append(extract_features_vector(features_df.iloc[i]))
        X = np.array(X_list, dtype=np.float32)
        y = labels

        # Filter valid indices (excluding unlabelled tail)
        valid_idx = np.arange(len(y) - 4)
        X_train = X[valid_idx]
        y_train = y[valid_idx]

        # Fit RobustScaler
        X_train_scaled = self.scaler.fit_transform(X_train)

        # Incorporate Hard Negative Mining & Wrong Trades Sample Weights
        sample_weights = np.ones(len(y_train), dtype=np.float32)
        
        # If we have stored wrong trades, add them as high-priority negative examples
        if len(self.wrong_trades) > 0 and len(self.wrong_trade_vectors) > 0:
            mistake_X = np.array(self.wrong_trade_vectors, dtype=np.float32)
            mistake_y = []
            mistake_weights = []

            for wt in self.wrong_trades:
                # If bot wrongly took a BUY, the corrected label is HOLD (0) or SELL (2)
                wrong_dir = wt.get("direction", "BUY")
                corrected_label = 2 if wrong_dir == "BUY" else 1
                mistake_y.append(corrected_label)
                mistake_weights.append(settings.MISTAKE_PENALTY_WEIGHT)

            mistake_X_scaled = self.scaler.transform(mistake_X)
            X_train_scaled = np.vstack([X_train_scaled, mistake_X_scaled])
            y_train = np.concatenate([y_train, np.array(mistake_y, dtype=int)])
            sample_weights = np.concatenate([sample_weights, np.array(mistake_weights, dtype=np.float32)])

        # Train model
        self.model.fit(X_train_scaled, y_train, sample_weight=sample_weights)
        self.is_trained = True
        self.retrain_count += 1
        self.last_trained_time = time.strftime("%Y-%m-%d %H:%M:%S")

        preds = self.model.predict(X_train_scaled)
        self.training_accuracy = round(float(accuracy_score(y_train, preds)) * 100, 2)

        return {
            "status": "success",
            "accuracy": self.training_accuracy,
            "retrain_count": self.retrain_count,
            "last_trained": self.last_trained_time,
            "wrong_trades_incorporated": len(self.wrong_trades)
        }

    def predict_signal(self, current_row: pd.Series) -> Tuple[str, float]:
        """
        Generates AI trading decision ('BUY', 'SELL', 'HOLD') and confidence score [0.0 - 1.0].
        """
        if not self.is_trained:
            return "HOLD", 0.0

        vec = extract_features_vector(current_row).reshape(1, -1)
        vec_scaled = self.scaler.transform(vec)

        probs = self.model.predict_proba(vec_scaled)[0]
        # Classes: 0 -> HOLD, 1 -> BUY, 2 -> SELL
        hold_p = probs[0] if len(probs) > 0 else 1.0
        buy_p = probs[1] if len(probs) > 1 else 0.0
        sell_p = probs[2] if len(probs) > 2 else 0.0

        if buy_p > 0.48 and buy_p > sell_p and buy_p > hold_p:
            return "BUY", float(buy_p)
        elif sell_p > 0.48 and sell_p > buy_p and sell_p > hold_p:
            return "SELL", float(sell_p)
        else:
            return "HOLD", float(hold_p)

    def evaluate_negative_shield(self, current_row: pd.Series, proposed_signal: str) -> Tuple[bool, str]:
        """
        Negative Pattern Shield:
        Compares current market state against past wrong trades.
        If similarity to a failed setup is dangerously high, VETO the trade!
        """
        if proposed_signal == "HOLD" or len(self.wrong_trades) == 0:
            return False, ""

        vec = extract_features_vector(current_row)
        norm_vec = np.linalg.norm(vec) + 1e-8

        for wt in self.wrong_trades[-30:]:  # Check against recent 30 wrong trades
            if wt.get("direction") == proposed_signal:
                past_vec = np.array(wt.get("features_at_entry", []), dtype=np.float32)
                if len(past_vec) == len(vec):
                    norm_past = np.linalg.norm(past_vec) + 1e-8
                    # Cosine similarity
                    cos_sim = float(np.dot(vec, past_vec) / (norm_vec * norm_past))
                    
                    if cos_sim >= settings.NEGATIVE_SHIELD_SIMILARITY_THRESHOLD:
                        self.vetoed_trades_count += 1
                        trade_id = wt.get("id", "UNKNOWN")
                        reason = wt.get("loss_cause", "similar false setup")
                        veto_msg = (
                            f"Vetoed by Negative Shield: {round(cos_sim*100, 1)}% pattern similarity "
                            f"to past failed Trade #{trade_id} ({reason})"
                        )
                        self.last_veto_reason = veto_msg
                        self._save_memory()
                        return True, veto_msg

        return False, ""

    def log_wrong_trade(
        self,
        trade_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        features_at_entry: np.ndarray,
        market_regime: str,
        strategy_used: str
    ):
        """
        Registers a failed trade into the mistake memory, diagnoses root-cause,
        and schedules live model retraining!
        """
        # Diagnose cause of failure based on features at entry
        loss_cause = self._diagnose_loss(features_at_entry, direction, market_regime)

        record = {
            "id": trade_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": round(pnl, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "strategy": strategy_used,
            "regime": market_regime,
            "loss_cause": loss_cause,
            "features_at_entry": features_at_entry.tolist()
        }

        self.wrong_trades.append(record)
        self.wrong_trade_vectors.append(features_at_entry)
        self._save_memory()
        print(f"[MLEngine] 🚨 Mistake logged: Trade #{trade_id} failed with ${pnl:.2f}. Cause: {loss_cause}")

    def _diagnose_loss(self, vec: np.ndarray, direction: str, regime: str) -> str:
        """Rule-based quantitative diagnostics of why the setup failed."""
        try:
            # Indices mapped to FEATURE_COLUMNS
            rsi_idx = FEATURE_COLUMNS.index("rsi_14")
            atr_ratio_idx = FEATURE_COLUMNS.index("atr_ratio")
            vol_ratio_idx = FEATURE_COLUMNS.index("vol_ratio")
            adx_idx = FEATURE_COLUMNS.index("adx")

            rsi = vec[rsi_idx]
            atr_ratio = vec[atr_ratio_idx]
            vol_ratio = vec[vol_ratio_idx]
            adx = vec[adx_idx]

            if direction == "BUY" and rsi > 70:
                return "Bought into Overbought RSI Exhaustion"
            elif direction == "SELL" and rsi < 30:
                return "Sold into Oversold RSI Bounce"
            elif "COMPRESSION" in regime or "CHOP" in regime:
                return "False Breakout during Low Volatility Squeeze"
            elif vol_ratio < 0.6:
                return "Lack of Volume Confirmation (Liquidity Trap)"
            elif adx < 18:
                return "Traded without Directional Trend (Whipsaw)"
            else:
                return f"Adverse Momentum Shift in {regime}"
        except Exception:
            return "Adverse Market Reversal"

    def get_stats(self) -> dict:
        return {
            "is_trained": self.is_trained,
            "parameters_count": self.total_parameters,
            "training_accuracy": self.training_accuracy,
            "retrain_count": self.retrain_count,
            "last_trained_time": self.last_trained_time or "Not yet trained",
            "wrong_trades_memorized": len(self.wrong_trades),
            "vetoed_trades_count": self.vetoed_trades_count,
            "last_veto_reason": self.last_veto_reason
        }

ml_engine = MLEngine()
