import pytest
from bot.risk.risk_manager import risk_manager
from bot.risk.circuit_breakers import circuit_breaker_manager
from bot.execution.models import InstrumentSpecification
from bot.risk.models import RiskDecision

@pytest.fixture(autouse=True)
def clean_circuit_breakers():
    circuit_breaker_manager.reset_all()
    risk_manager.reset_daily_baseline(10000.0)
    yield
    circuit_breaker_manager.reset_all()

def test_pre_trade_gates_approved_when_all_healthy():
    spec = InstrumentSpecification(symbol="EURUSD", min_volume=0.01, contract_size=100000.0)
    res = risk_manager.evaluate_pre_trade_gates(
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        sl_price=1.0800,
        spec=spec,
        open_positions=[],
        current_spread_points=1.5,
        max_allowed_spread_points=20.0,
        feed_latency_seconds=1.0,
        broker_connected=True
    )
    assert res.approved is True
    assert res.decision == RiskDecision.APPROVED
    assert res.recommended_size > 0
    assert len(res.failed_gates) == 0

def test_circuit_breaker_tripped_vetoes_trade():
    circuit_breaker_manager.trip("TEST_INCIDENT", "Simulated critical failure")
    spec = InstrumentSpecification(symbol="EURUSD", min_volume=0.01)

    res = risk_manager.evaluate_pre_trade_gates(
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        sl_price=1.0800,
        spec=spec,
        open_positions=[]
    )
    assert res.approved is False
    assert "CircuitBreakerGate" in res.failed_gates
    assert res.recommended_size == 0.0

def test_daily_drawdown_limit_triggers_breaker():
    risk_manager.reset_daily_baseline(10000.0)
    # 5% max daily drawdown on 10,000 = $9,500. Drop equity to $9,400 (6% loss)
    risk_manager.update_equity(9400.0)

    assert risk_manager.daily_drawdown_limit_hit is True
    assert circuit_breaker_manager.is_tripped() is True

def test_spread_filter_vetoes_trade():
    spec = InstrumentSpecification(symbol="EURUSD", min_volume=0.01)
    res = risk_manager.evaluate_pre_trade_gates(
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        sl_price=1.0800,
        spec=spec,
        open_positions=[],
        current_spread_points=45.0,  # Huge spread
        max_allowed_spread_points=20.0
    )
    assert res.approved is False
    assert "SpreadGate" in res.failed_gates

def test_stale_market_feed_vetoes_trade():
    spec = InstrumentSpecification(symbol="EURUSD", min_volume=0.01)
    res = risk_manager.evaluate_pre_trade_gates(
        symbol="EURUSD",
        side="BUY",
        entry_price=1.0850,
        sl_price=1.0800,
        spec=spec,
        open_positions=[],
        feed_latency_seconds=45.0,  # 45s latency
        max_feed_latency_seconds=15.0
    )
    assert res.approved is False
    assert "DataFreshnessGate" in res.failed_gates

def test_trailing_stop_tightens_only_in_profit():
    # BUY trade entered at 1.0800, SL at 1.0750
    # Price rises to 1.0900 (100 pips profit, ATR = 20 pips = 0.0020)
    new_sl = risk_manager.evaluate_trailing_stop(
        position_type="BUY",
        entry_price=1.0800,
        current_price=1.0900,
        current_sl=1.0750,
        atr=0.0020
    )
    assert new_sl is not None
    assert new_sl > 1.0750  # Must tighten

    # If price drops, trailing stop NEVER loosens
    worse_sl = risk_manager.evaluate_trailing_stop(
        position_type="BUY",
        entry_price=1.0800,
        current_price=1.0770,
        current_sl=1.0820,
        atr=0.0020
    )
    assert worse_sl is None

def test_evaluate_news_volatility_shield_exists_and_runs():
    from bot.data.news_feed import news_feed_engine
    is_vetoed, reason = news_feed_engine.evaluate_news_volatility_shield("EURUSD")
    assert isinstance(is_vetoed, bool)
    if is_vetoed:
        assert isinstance(reason, str)
