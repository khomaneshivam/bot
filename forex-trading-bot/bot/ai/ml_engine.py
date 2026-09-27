import os
import json
import time
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from bot.ai.features import compute_all_features, extract_features_vector, FEATURE_COLUMNS
from bot.ai.model_registry import model_registry
from bot.config.settings import settings

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "wrong_trades_memory.json")

class MLEngine:
    """
    Production-grade Quantitative ML Engine.
    Features:
    - Chronological Walk-Forward validation (Train -> Val/Calibration -> OOS Test).
    - Probability calibration via Platt scaling / Sigmoid CalibratedClassifierCV.
    - Rigorous metrics: Brier score, Log loss, OOS Accuracy.
    - Model Registry versioning (Champion / Challenger).
    - Hard negative pattern shield without unsafe single-trade retrains.
    """

    def __init__(self):
        self.scaler = RobustScaler()
        self.base_model = HistGradientBoostingClassifier(
            max_iter=150,
            learning_rate=0.05,
            max_depth=5,
            min_samples_leaf=20,
            l2_regularization=2.0,
            random_state=42
        )
        self.calibrated_model: Optional[CalibratedClassifierCV] = None
        self.is_trained = False
        self.version = "1.0.0"
        self.last_trained_time: Optional[str] = None
        self.training_accuracy: float = 0.0
        self.oos_accuracy: float = 0.0
        self.brier_score: float = 0.0
        self.log_loss_score: float = 0.0
        self.retrain_count: int = 0

        # Negative Pattern Shield Memory
        self.wrong_trades: List[Dict] = []
        self.wrong_trade_vectors: List[np.ndarray] = []
        self.vetoed_trades_count: int = 0
        self.last_veto_reason: str = ""

        self._load_memory()

    def _load_memory(self):
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
                print(f"[MLEngine] Memory load notice: {e}")

    def _save_memory(self):
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
        Creates strictly causal target labels:
        1 = BUY breakout
        2 = SELL breakdown
        0 = HOLD / Chop
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
                labels[i] = 2   # SELL
            else:
                labels[i] = 0   # HOLD

        return labels

    def train_walk_forward(self, df: pd.DataFrame) -> dict:
        """
        Chronological Walk-Forward Training & Calibration:
        - 60% Train (Base model fitting)
        - 20% Validation (Probability calibration via Sigmoid/Platt)
        - 20% Untouched Out-Of-Sample Test (Brier score & Generalization verification)
        """
        if len(df) < 100:
            return {"status": "error", "message": "Insufficient data for chronological validation (min 100 bars)"}

        features_df = compute_all_features(df)
        labels = self.generate_labels(features_df)

        # Exclude forward looking tail
        valid_len = len(features_df) - 4
        X_list = [extract_features_vector(features_df.iloc[i]) for i in range(valid_len)]
        X = np.array(X_list, dtype=np.float32)
        y = labels[:valid_len]

        # Chronological splits
        train_end = int(valid_len * 0.60)
        val_end = int(valid_len * 0.80)

        X_train, y_train = X[:train_end], y[:train_end]
        X_val, y_val = X[train_end:val_end], y[train_end:val_end]
        X_test, y_test = X[val_end:], y[val_end:]

        if len(X_train) < 20 or len(X_val) < 10 or len(X_test) < 10:
            return {"status": "error", "message": "Split sets too small"}

        # Fit Scaler on TRAIN ONLY (Strictly zero lookahead leakage)
        X_train_s = self.scaler.fit_transform(X_train)
        X_val_s = self.scaler.transform(X_val)
        X_test_s = self.scaler.transform(X_test)

        # 1. Fit Base Estimator on Train
        self.base_model.fit(X_train_s, y_train)

        # 2. Fit CalibratedClassifierCV on Validation (Platt Scaling)
        # Note: if validation set does not contain all classes, fallback gracefully
        unique_train = set(np.unique(y_train))
        unique_val = set(np.unique(y_val))

        if unique_val.issubset(unique_train) and len(unique_val) >= 2:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=FutureWarning)
                try:
                    try:
                        from sklearn.frozen import FrozenEstimator
                        self.calibrated_model = CalibratedClassifierCV(
                            estimator=FrozenEstimator(self.base_model),
                            method="sigmoid"
                        )
                    except ImportError:
                        self.calibrated_model = CalibratedClassifierCV(
                            estimator=self.base_model,
                            method="sigmoid",
                            cv="prefit"
                        )
                    self.calibrated_model.fit(X_val_s, y_val)
                except Exception:
                    self.calibrated_model = None
        else:
            self.calibrated_model = None

        # 3. Evaluate on Untouched OOS Test Set
        active_model = self.calibrated_model if self.calibrated_model else self.base_model
        test_preds = active_model.predict(X_test_s)
        test_probs = active_model.predict_proba(X_test_s)

        self.oos_accuracy = round(float(accuracy_score(y_test, test_preds)) * 100, 2)
        train_preds = self.base_model.predict(X_train_s)
        self.training_accuracy = round(float(accuracy_score(y_train, train_preds)) * 100, 2)

        # Compute multi-class Brier score
        brier_sum = 0.0
        n_classes = test_probs.shape[1]
        for c_idx in range(n_classes):
            y_binary = (y_test == c_idx).astype(int)
            brier_sum += brier_score_loss(y_binary, test_probs[:, c_idx])
        self.brier_score = round(float(brier_sum / max(n_classes, 1)), 4)

        try:
            self.log_loss_score = round(float(log_loss(y_test, test_probs)), 4)
        except Exception:
            self.log_loss_score = 0.0

        self.is_trained = True
        self.retrain_count += 1
        self.last_trained_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.version = f"1.{self.retrain_count}.0"

        # 4. Register in Model Registry
        model_bytes = pickle.dumps(active_model)
        model_registry.register_model(
            version=self.version,
            model_type="HistGradientBoosting+Platt",
            stage="CHAMPION" if self.retrain_count == 1 else "CHALLENGER",
            hyperparameters={
                "learning_rate": 0.05,
                "max_depth": 5,
                "l2_regularization": 2.0
            },
            validation_accuracy=self.oos_accuracy,
            brier_score=self.brier_score,
            log_loss=self.log_loss_score,
            model_bytes=model_bytes
        )

        return {
            "status": "success",
            "version": self.version,
            "train_accuracy": self.training_accuracy,
            "oos_accuracy": self.oos_accuracy,
            "brier_score": self.brier_score,
            "log_loss": self.log_loss_score,
            "retrain_count": self.retrain_count,
            "calibrated": self.calibrated_model is not None,
            "last_trained": self.last_trained_time
        }

    def train_on_data(self, df: pd.DataFrame) -> dict:
        """Alias redirecting to chronological walk-forward training."""
        return self.train_walk_forward(df)

    def predict_signal(self, current_row: pd.Series) -> Tuple[str, float, float]:
        """
        Generates trading decision ('BUY', 'SELL', 'HOLD'), calibrated probability,
        and raw model confidence score.
        Returns: (signal, calibrated_probability, raw_confidence)
        """
        if not self.is_trained:
            return "HOLD", 0.0, 0.0

        vec = extract_features_vector(current_row).reshape(1, -1)
        vec_scaled = self.scaler.transform(vec)

        active_model = self.calibrated_model if self.calibrated_model else self.base_model
        probs = active_model.predict_proba(vec_scaled)[0]

        # Classes: 0 -> HOLD, 1 -> BUY, 2 -> SELL
        hold_p = probs[0] if len(probs) > 0 else 1.0
        buy_p = probs[1] if len(probs) > 1 else 0.0
        sell_p = probs[2] if len(probs) > 2 else 0.0

        if buy_p > 0.45 and buy_p > sell_p and buy_p > hold_p:
            return "BUY", float(buy_p), float(buy_p)
        elif sell_p > 0.45 and sell_p > buy_p and sell_p > hold_p:
            return "SELL", float(sell_p), float(sell_p)
        else:
            return "HOLD", float(hold_p), float(max(hold_p, buy_p, sell_p))

    def evaluate_negative_shield(self, current_row: pd.Series, proposed_signal: str) -> Tuple[bool, str]:
        """
        Negative Pattern Shield: Vetoes proposed signal if cosine similarity to past losing trade >= 0.88.
        """
        if proposed_signal == "HOLD" or len(self.wrong_trades) == 0:
            return False, ""

        vec = extract_features_vector(current_row)
        norm_vec = np.linalg.norm(vec) + 1e-8

        for wt in self.wrong_trades[-30:]:
            if wt.get("direction") == proposed_signal:
                past_vec = np.array(wt.get("features_at_entry", []), dtype=np.float32)
                if len(past_vec) == len(vec):
                    norm_past = np.linalg.norm(past_vec) + 1e-8
                    sim = float(np.dot(vec, past_vec) / (norm_vec * norm_past))
                    if sim >= 0.88:
                        reason = f"Negative pattern match ({sim*100:.1f}%) to failed trade #{wt.get('id')}"
                        self.vetoed_trades_count += 1
                        self.last_veto_reason = reason
                        self._save_memory()
                        return True, reason
        return False, ""

    def log_wrong_trade(
        self,
        trade_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        strategy_used: str,
        market_regime: str,
        features_at_entry: np.ndarray
    ):
        """
        Logs losing trade into memory for forensic tracking and negative pattern shielding.
        NOTE: Does NOT trigger immediate retrain, avoiding overfitting to noise.
        """
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
            "features_at_entry": features_at_entry.tolist() if isinstance(features_at_entry, np.ndarray) else features_at_entry
        }

        self.wrong_trades.append(record)
        if isinstance(features_at_entry, np.ndarray):
            self.wrong_trade_vectors.append(features_at_entry)
        self._save_memory()
        print(f"[MLEngine] 🚨 Mistake logged: Trade #{trade_id} failed with ${pnl:.2f}. Shield memory updated.")

    def get_stats(self) -> dict:
        return {
            "is_trained": self.is_trained,
            "version": self.version,
            "training_accuracy": self.training_accuracy,
            "oos_accuracy": self.oos_accuracy,
            "brier_score": self.brier_score,
            "log_loss": self.log_loss_score,
            "calibrated": self.calibrated_model is not None,
            "retrain_count": self.retrain_count,
            "last_trained_time": self.last_trained_time or "Not yet trained",
            "wrong_trades_memorized": len(self.wrong_trades),
            "vetoed_trades_count": self.vetoed_trades_count,
            "last_veto_reason": self.last_veto_reason
        }

ml_engine = MLEngine()
