import time
from typing import Tuple, Dict, List, Optional, Any
from bot.config.settings import settings
from bot.execution.models import InstrumentSpecification
from bot.risk.models import RiskDecision, RiskCheckResult
from bot.risk.circuit_breakers import circuit_breaker_manager
from bot.risk.sizing import calculate_broker_aware_position_size

class RiskManager:
    """
    Dedicated Institutional Risk Management Engine.
    Executes 9 deterministic risk gates before every trade.
    Enforces independent circuit breakers and broker-aware position sizing.
    """

    def __init__(self):
        self.daily_starting_equity: float = settings.PAPER_STARTING_BALANCE
        self.current_equity: float = settings.PAPER_STARTING_BALANCE
        self.daily_drawdown_limit_hit: bool = False
        self.max_daily_drawdown_pct: float = settings.MAX_DAILY_DRAWDOWN_PERCENT
        self.max_risk_per_trade_pct: float = settings.MAX_RISK_PER_TRADE_PERCENT
        self.max_concurrent_positions: int = settings.MAX_OPEN_POSITIONS_OVERALL
        self.max_symbol_positions: int = settings.MAX_OPEN_POSITIONS_PER_PAIR

    def reset_daily_baseline(self, equity: float):
        """Sets new starting baseline for daily drawdown calculation."""
        self.daily_starting_equity = equity
        self.current_equity = equity
        self.daily_drawdown_limit_hit = False

    def update_equity(self, equity: float):
        """Monitors equity and trips the daily drawdown circuit breaker if threshold breached."""
        self.current_equity = equity
        if self.daily_starting_equity > 0:
            dd_pct = ((self.daily_starting_equity - self.current_equity) / self.daily_starting_equity) * 100.0
            if dd_pct >= self.max_daily_drawdown_pct:
                self.daily_drawdown_limit_hit = True
                circuit_breaker_manager.trip(
                    "DAILY_DRAWDOWN_LIMIT",
                    f"Daily drawdown reached {dd_pct:.2f}% (Limit: {self.max_daily_drawdown_pct}%)"
                )

    def calculate_position_size(
        self,
        equity: float,
        entry_price: float,
        sl_price: float,
        spec: InstrumentSpecification,
        max_leverage: float = 30.0
    ) -> Tuple[float, Dict[str, float]]:
        """Calculates broker-aware position size."""
        if self.daily_drawdown_limit_hit or circuit_breaker_manager.is_tripped():
            return 0.0, {"error": "Trading halted by risk engine."}

        return calculate_broker_aware_position_size(
            equity=equity,
            risk_percent=self.max_risk_per_trade_pct,
            entry_price=entry_price,
            sl_price=sl_price,
            spec=spec,
            max_leverage=max_leverage
        )

    def evaluate_pre_trade_gates(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        sl_price: float,
        spec: InstrumentSpecification,
        open_positions: List[Dict],
        current_spread_points: float = 1.0,
        max_allowed_spread_points: float = 40.0,
        feed_latency_seconds: float = 0.5,
        max_feed_latency_seconds: float = 15.0,
        broker_connected: bool = True
    ) -> RiskCheckResult:
        """
        Executes 9 deterministic pre-trade risk gates.
        Returns a structured RiskCheckResult.
        """
        passed = []
        failed = []
        details = {}

        # Gate 1: Hard Circuit Breakers
        if circuit_breaker_manager.is_tripped():
            failed.append("CircuitBreakerGate")
            status = circuit_breaker_manager.get_status()
            details["circuit_breaker"] = str(status.active_breakers)
        else:
            passed.append("CircuitBreakerGate")

        # Gate 2: Daily Drawdown Limit
        if self.daily_drawdown_limit_hit:
            failed.append("DrawdownLimitGate")
            details["drawdown"] = "Daily drawdown limit exceeded"
        else:
            passed.append("DrawdownLimitGate")

        # Gate 3: Max Concurrent Portfolio Positions
        if len(open_positions) >= self.max_concurrent_positions:
            failed.append("MaxPositionsGate")
            details["max_positions"] = f"Open {len(open_positions)} >= Max {self.max_concurrent_positions}"
        else:
            passed.append("MaxPositionsGate")

        # Gate 4: Single Symbol Exposure
        symbol_positions = [p for p in open_positions if p.get("symbol") == symbol]
        if len(symbol_positions) >= self.max_symbol_positions:
            failed.append("SymbolExposureGate")
            details["symbol_exposure"] = f"Open on {symbol}: {len(symbol_positions)} >= Max {self.max_symbol_positions}"
        else:
            passed.append("SymbolExposureGate")

        # Gate 5: Broker Connectivity
        if not broker_connected:
            failed.append("BrokerHealthGate")
            details["broker_health"] = "Broker is disconnected or unhealthy"
        else:
            passed.append("BrokerHealthGate")

        # Gate 6: Data Feed Freshness
        if feed_latency_seconds > max_feed_latency_seconds:
            failed.append("DataFreshnessGate")
            details["data_freshness"] = f"Latency {feed_latency_seconds:.1f}s > Max {max_feed_latency_seconds:.1f}s"
        else:
            passed.append("DataFreshnessGate")

        # Gate 7: Market Spread Filter
        if current_spread_points > max_allowed_spread_points:
            failed.append("SpreadGate")
            details["spread"] = f"Spread {current_spread_points} > Max {max_allowed_spread_points}"
        else:
            passed.append("SpreadGate")

        # Gate 8: Stop-Loss Validity
        stop_dist = abs(entry_price - sl_price)
        min_stop = spec.tick_size * 5
        if stop_dist < min_stop:
            failed.append("StopLossGate")
            details["stop_loss"] = f"Stop distance {stop_dist:.5f} is below minimum {min_stop:.5f}"
        else:
            passed.append("StopLossGate")

        # Gate 9: Sizing Verification
        recommended_size, size_metrics = self.calculate_position_size(
            equity=self.current_equity,
            entry_price=entry_price,
            sl_price=sl_price,
            spec=spec
        )
        if recommended_size <= 0:
            failed.append("PositionSizingGate")
            details["sizing"] = size_metrics.get("error", "Calculated size is zero")
        else:
            passed.append("PositionSizingGate")

        approved = len(failed) == 0
        decision = RiskDecision.APPROVED if approved else RiskDecision.REJECTED
        rejection_reason = "; ".join([f"{k}: {v}" for k, v in details.items()]) if not approved else None

        return RiskCheckResult(
            decision=decision,
            approved=approved,
            recommended_size=recommended_size if approved else 0.0,
            passed_gates=passed,
            failed_gates=failed,
            rejection_reason=rejection_reason,
            details=details
        )

    def evaluate_trailing_stop(
        self,
        position_type: str,
        entry_price: float,
        current_price: float,
        current_sl: float,
        atr: float
    ) -> Optional[float]:
        """
        Dynamic trailing stop: If position moved in favor by >= 1.5 ATR,
        tighten stop to lock in profits. Stops can only move in favor of position.
        """
        if not settings.TRAILING_STOP_ENABLED or atr <= 0:
            return None

        trail_distance = atr * 1.2

        if position_type.upper() == "BUY":
            profit_points = current_price - entry_price
            if profit_points >= atr * settings.TRAILING_STOP_ACTIVATION_R:
                new_sl = round(current_price - trail_distance, 4)
                if new_sl > current_sl:
                    return new_sl
        elif position_type.upper() == "SELL":
            profit_points = entry_price - current_price
            if profit_points >= atr * settings.TRAILING_STOP_ACTIVATION_R:
                new_sl = round(current_price + trail_distance, 4)
                if new_sl < current_sl:
                    return new_sl

        return None

risk_manager = RiskManager()