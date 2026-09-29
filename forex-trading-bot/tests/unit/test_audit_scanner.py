import pytest
import asyncio
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from bot.strategies.ensemble import StrategyEnsemble
from bot.ai.features import compute_all_features
from bot.ai.audit_scanner import MarketAuditScanner


def _make_sample_candles(n_bars: int = 50) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01", periods=n_bars, freq="5min")
    prices = [1.1000 + i * 0.0002 for i in range(n_bars)]
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": [p - 0.0001 for p in prices],
        "high": [p + 0.0003 for p in prices],
        "low": [p - 0.0003 for p in prices],
        "close": prices,
        "volume": [1000.0] * n_bars
    })


def test_evaluate_smart_money_without_is_bull_candle_column():
    """Ensure evaluate_smart_money never raises KeyError: 'is_bull_candle' on raw OHLCV."""
    ensemble = StrategyEnsemble()
    raw_df = _make_sample_candles(35)
    assert "is_bull_candle" not in raw_df.columns

    signal, conf = ensemble.evaluate_smart_money(raw_df)
    assert signal in ["BUY", "SELL", "HOLD"]
    assert 0.0 <= conf <= 1.0


def test_compute_all_features_short_dataframe():
    """Ensure compute_all_features populates basic candlestick metrics even if < 30 rows."""
    short_df = _make_sample_candles(20)
    features = compute_all_features(short_df)
    assert features is not None
    assert len(features) == 20
    assert "is_bull_candle" in features.columns
    assert "candle_body_ratio" in features.columns
    assert "upper_shadow_ratio" in features.columns
    assert "lower_shadow_ratio" in features.columns


def test_evaluate_pair_strategies_short_or_none():
    """Ensure evaluate_pair_strategies gracefully returns default equilibrium dictionary."""
    scanner = MarketAuditScanner()

    # None DataFrame
    res_none = scanner.evaluate_pair_strategies("EURUSD", None)
    assert res_none["symbol"] == "EURUSD"
    assert res_none["overall_signal"] == "HOLD"
    assert res_none["badge_class"] == "badge-dormant"

    # Short DataFrame (< 30 candles)
    short_df = _make_sample_candles(20)
    res_short = scanner.evaluate_pair_strategies("GBPUSD", short_df)
    assert res_short["symbol"] == "GBPUSD"
    assert res_short["overall_signal"] == "HOLD"
    assert res_short["price"] > 0.0

    # Adequate DataFrame (>= 30 candles)
    full_df = _make_sample_candles(50)
    res_full = scanner.evaluate_pair_strategies("USDJPY", full_df)
    assert res_full["symbol"] == "USDJPY"
    assert "strategies" in res_full
    assert "Smart_Money_SMC" in res_full["strategies"]


def test_run_full_market_audit_no_unhandled_exception():
    """Ensure run_full_market_audit runs to completion even if market_feed returns short/empty data."""
    scanner = MarketAuditScanner()
    short_df = _make_sample_candles(18)

    with patch("bot.ai.audit_scanner.market_feed.get_candles", return_value=short_df):
        with patch.object(scanner, "ALL_PAIRS", ["EURUSD", "GBPUSD"]):
            audit_result = asyncio.run(scanner.run_full_market_audit())
            assert audit_result is not None
            assert "audit_records" in audit_result
            assert len(audit_result["audit_records"]) == 2
            for record in audit_result["audit_records"]:
                assert "symbol" in record
                assert "overall_signal" in record
