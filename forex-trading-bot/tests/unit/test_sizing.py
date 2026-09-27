import pytest
from bot.execution.models import InstrumentSpecification
from bot.risk.sizing import calculate_broker_aware_position_size

def test_forex_position_sizing_standard_lot():
    eurusd_spec = InstrumentSpecification(
        symbol="EURUSD",
        tick_size=0.00001,
        tick_value=1.0,
        contract_size=100000.0,
        min_volume=0.01,
        max_volume=50.0,
        volume_step=0.01,
        base_currency="EUR",
        quote_currency="USD",
        is_crypto=False
    )

    equity = 10000.0
    risk_pct = 1.0  # $100 risk
    entry = 1.08500
    sl = 1.08000    # 50 pips = 5000 ticks

    vol, metrics = calculate_broker_aware_position_size(
        equity=equity,
        risk_percent=risk_pct,
        entry_price=entry,
        sl_price=sl,
        spec=eurusd_spec
    )

    assert vol > 0
    assert vol >= eurusd_spec.min_volume
    assert vol <= eurusd_spec.max_volume
    assert metrics["risk_budget"] == 100.0
    assert "ticks_at_risk" in metrics

def test_crypto_position_sizing_btc():
    btc_spec = InstrumentSpecification(
        symbol="BTCUSDT",
        tick_size=0.01,
        tick_value=0.01,
        contract_size=1.0,
        min_volume=0.001,
        max_volume=10.0,
        volume_step=0.001,
        base_currency="BTC",
        quote_currency="USDT",
        is_crypto=True
    )

    equity = 5000.0
    risk_pct = 2.0  # $100 risk
    entry = 80000.0
    sl = 78000.0    # $2000 stop distance

    vol, metrics = calculate_broker_aware_position_size(
        equity=equity,
        risk_percent=risk_pct,
        entry_price=entry,
        sl_price=sl,
        spec=btc_spec
    )

    assert vol > 0
    assert vol >= btc_spec.min_volume
    # $100 / $2000.02 ~ 0.049 BTC
    assert 0.040 <= vol <= 0.060

def test_zero_stop_distance_returns_zero():
    spec = InstrumentSpecification(symbol="EURUSD")
    vol, metrics = calculate_broker_aware_position_size(
        equity=10000.0,
        risk_percent=1.0,
        entry_price=1.0800,
        sl_price=1.0800,
        spec=spec
    )
    assert vol == 0.0
    assert "error" in metrics

def test_leverage_limit_capping():
    spec = InstrumentSpecification(
        symbol="BTCUSDT",
        tick_size=0.01,
        contract_size=1.0,
        min_volume=0.001,
        volume_step=0.001,
        is_crypto=True
    )
    equity = 1000.0
    risk_pct = 5.0
    entry = 100.0
    sl = 99.9  # tiny stop distance would suggest huge size without leverage cap

    vol, metrics = calculate_broker_aware_position_size(
        equity=equity,
        risk_percent=risk_pct,
        entry_price=entry,
        sl_price=sl,
        spec=spec,
        max_leverage=5.0  # Max notional = $5000 => 50 units
    )

    assert vol <= 50.0

def test_position_sizing_resilience_to_boolean_is_crypto():
    """Verifies that calculate_broker_aware_position_size never crashes when spec is bool or None."""
    # Test with spec=True (crypto bool)
    vol_crypto, metrics_crypto = calculate_broker_aware_position_size(
        equity=1000.0,
        risk_percent=2.0,
        entry_price=50000.0,
        sl_price=49000.0,
        spec=True
    )
    assert vol_crypto > 0

    # Test with spec=False (forex bool)
    vol_forex, metrics_forex = calculate_broker_aware_position_size(
        equity=10000.0,
        risk_percent=2.0,
        entry_price=1.1000,
        sl_price=1.0950,
        spec=False
    )
    assert vol_forex > 0

    # Test with spec=None
    vol_none, metrics_none = calculate_broker_aware_position_size(
        equity=10000.0,
        risk_percent=2.0,
        entry_price=1.1000,
        sl_price=1.0950,
        spec=None
    )
    assert vol_none > 0

def test_risk_manager_calculate_position_size_returns_sized_volume():
    """Verifies RiskManager.calculate_position_size returns SizedVolume that works as float and 2-tuple."""
    from bot.risk.risk_manager import risk_manager

    # 1. As float in boolean comparison
    size = risk_manager.calculate_position_size(
        equity=1000.0,
        entry_price=50000.0,
        sl_price=49000.0,
        spec=True
    )
    assert size > 0
    assert float(size) > 0

    # 2. As unpacked tuple
    vol, metrics = risk_manager.calculate_position_size(
        equity=1000.0,
        entry_price=50000.0,
        sl_price=49000.0,
        spec=True
    )
    assert vol == float(size)
    assert isinstance(metrics, dict)
