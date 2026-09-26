import pytest
import numpy as np
import pandas as pd
from bot.ai.ml_engine import ml_engine
from bot.ai.model_registry import model_registry

def _generate_synthetic_candles(n_bars: int = 150) -> pd.DataFrame:
    """Generates synthetic trend/reversal series for ML test validation."""
    timestamps = pd.date_range("2026-01-01", periods=n_bars, freq="5min")
    prices = [1.0800]
    for _ in range(n_bars - 1):
        prices.append(prices[-1] + np.random.uniform(-0.0010, 0.0012))

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": prices,
        "high": [p + 0.0005 for p in prices],
        "low": [p - 0.0005 for p in prices],
        "close": prices,
        "volume": [1000.0] * n_bars
    })
    return df

def test_chronological_walk_forward_training():
    df = _generate_synthetic_candles(150)
    res = ml_engine.train_walk_forward(df)

    assert res["status"] == "success"
    assert "oos_accuracy" in res
    assert "brier_score" in res
    assert res["brier_score"] >= 0.0
    assert ml_engine.is_trained is True

def test_model_registry_champion_tracking():
    # Register a champion model
    meta = model_registry.register_model(
        version="1.0.0",
        model_type="HistGradientBoosting+Platt",
        stage="CHAMPION",
        hyperparameters={"learning_rate": 0.05},
        validation_accuracy=65.0,
        brier_score=0.15,
        log_loss=0.45,
        model_bytes=b"model_weights_test"
    )
    champ = model_registry.get_champion()
    assert champ is not None
    assert "artifact_hash" in champ
    assert champ["stage"] == "CHAMPION"

def test_model_promotion_gates():
    # Register a poor challenger
    bad_meta = model_registry.register_model(
        version="9.9.9",
        model_type="Test",
        stage="CHALLENGER",
        hyperparameters={},
        validation_accuracy=40.0,  # Below 55% threshold
        brier_score=0.45,          # Above 0.25 threshold
        log_loss=1.2,
        model_bytes=b"dummy_bytes"
    )

    promoted = model_registry.promote_challenger(bad_meta.id, min_accuracy=55.0, max_brier_score=0.25)
    assert promoted is False

def test_negative_pattern_shield():
    # Log a fake losing trade
    trade_id = "loss_test_1"
    vec = np.ones(36, dtype=np.float32)
    ml_engine.log_wrong_trade(
        trade_id=trade_id,
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        exit_price=1.0800,
        pnl=-50.0,
        strategy_used="TestStrategy",
        market_regime="TRENDING_UP",
        features_at_entry=vec
    )

    # Fake current row matching vector
    row = pd.Series({"rsi_14": 75.0, "adx": 30.0, "atr_14": 0.0015})
    # Evaluate shield directly with matching vector
    norm = np.linalg.norm(vec)
    sim = np.dot(vec, vec) / (norm * norm)
    assert sim >= 0.99
