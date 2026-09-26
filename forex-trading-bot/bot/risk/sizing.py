import math
from typing import Tuple, Dict
from bot.execution.models import InstrumentSpecification

def calculate_broker_aware_position_size(
    equity: float,
    risk_percent: float,
    entry_price: float,
    sl_price: float,
    spec: InstrumentSpecification,
    max_leverage: float = 30.0,
    expected_slippage_ticks: float = 2.0
) -> Tuple[float, Dict[str, float]]:
    """
    Pure unit-testable broker-aware position sizing.
    Calculates exact risk budget, tick risk, volume step normalization, and leverage caps.

    Returns:
        (calculated_volume: float, sizing_metrics: dict)
    """
    if equity <= 0 or entry_price <= 0 or sl_price <= 0:
        return 0.0, {"error": "Invalid equity or price parameters"}

    # 1. Calculate monetary risk budget
    risk_budget = equity * (risk_percent / 100.0)

    # 2. Calculate stop distance and slippage allowance
    stop_distance = abs(entry_price - sl_price)
    if stop_distance <= 0:
        return 0.0, {"error": "Zero stop loss distance"}

    effective_stop_distance = stop_distance + (expected_slippage_ticks * spec.tick_size)
    ticks_at_risk = effective_stop_distance / max(spec.tick_size, 1e-8)

    # 3. Monetary risk per unit/lot
    if spec.is_crypto:
        monetary_risk_per_unit = effective_stop_distance
        raw_volume = risk_budget / max(monetary_risk_per_unit, 1e-6)
    else:
        # Standard financial lot sizing
        monetary_risk_per_lot = ticks_at_risk * spec.tick_value
        raw_volume = risk_budget / max(monetary_risk_per_lot, 1e-6)

    # 4. Volume step normalization
    steps = math.floor(raw_volume / spec.volume_step)
    stepped_volume = round(steps * spec.volume_step, 6)

    # 5. Check min volume and risk ceiling
    if stepped_volume < spec.min_volume:
        # If minimum volume exceeds 150% of allowable risk, reject for capital preservation
        min_vol_risk = (
            spec.min_volume * monetary_risk_per_unit
            if spec.is_crypto
            else (spec.min_volume * ticks_at_risk * spec.tick_value)
        )
        if min_vol_risk > risk_budget * 1.5:
            return 0.0, {
                "error": "Min volume risk exceeds risk budget",
                "risk_budget": risk_budget,
                "min_vol_risk": min_vol_risk
            }
        stepped_volume = spec.min_volume

    volume = min(stepped_volume, spec.max_volume)

    # 6. Leverage and Margin Constraints
    if spec.is_crypto:
        notional = volume * entry_price
    else:
        notional = volume * spec.contract_size * entry_price

    implied_leverage = notional / max(equity, 1.0)
    if implied_leverage > max_leverage:
        max_notional = equity * max_leverage
        if spec.is_crypto:
            max_vol = max_notional / entry_price
        else:
            max_vol = max_notional / (spec.contract_size * entry_price)
        steps = math.floor(max_vol / spec.volume_step)
        volume = round(steps * spec.volume_step, 6)

    volume = max(0.0, round(volume, 6))

    metrics = {
        "risk_budget": round(risk_budget, 2),
        "ticks_at_risk": round(ticks_at_risk, 2),
        "effective_stop_distance": round(effective_stop_distance, 5),
        "implied_leverage": round(implied_leverage, 2),
        "calculated_volume": volume
    }

    return volume, metrics
