import math
from typing import Tuple, Dict, Optional
from bot.config.settings import settings

class RiskManager:
    def __init__(self):
        self.daily_starting_equity: float = settings.PAPER_STARTING_BALANCE
        self.current_equity: float = settings.PAPER_STARTING_BALANCE
        self.daily_drawdown_limit_hit: bool = False

    def reset_daily_baseline(self, equity: float):
        self.daily_starting_equity = equity
        self.current_equity = equity
        self.daily_drawdown_limit_hit = False

    def update_equity(self, equity: float):
        self.current_equity = equity
        # Check daily drawdown
        if self.daily_starting_equity > 0:
            dd_pct = ((self.daily_starting_equity - self.current_equity) / self.daily_starting_equity) * 100.0
            if dd_pct >= settings.MAX_DAILY_DRAWDOWN_PERCENT:
                self.daily_drawdown_limit_hit = True
                print(f"[RiskManager] ⚠️ MAX DAILY DRAWDOWN REACHED ({dd_pct:.2f}% >= {settings.MAX_DAILY_DRAWDOWN_PERCENT}%). Kill switch triggered!")

    def calculate_position_size(
        self,
        equity: float,
        entry_price: float,
        sl_price: float,
        is_crypto: bool
    ) -> float:
        """
        Calculates position size strictly respecting MAX_RISK_PER_TRADE_PERCENT of equity.
        """
        if self.daily_drawdown_limit_hit:
            return 0.0

        risk_amount = equity * (settings.MAX_RISK_PER_TRADE_PERCENT / 100.0)
        risk_per_unit = abs(entry_price - sl_price)

        if risk_per_unit <= 1e-6:
            risk_per_unit = entry_price * 0.01

        units = risk_amount / risk_per_unit

        if is_crypto:
            # Cap total crypto notional position to max 40% of equity ($40 on $100 capital)
            max_notional = max(10.0, equity * 0.40)
            max_units = max_notional / max(entry_price, 1e-4)
            calc_units = min(units, max_units)
            if entry_price > 1000:
                return max(0.0001, round(calc_units, 4))
            elif entry_price > 10:
                return max(0.01, round(calc_units, 2))
            else:
                return max(0.5, round(calc_units, 1))
        else:
            # Standard Forex lot sizing (1 lot = 100,000 units)
            lots = units / 100000.0
            # Clip between 0.01 micro-lot and 0.05 lots for small capital
            return max(0.01, min(0.05, round(lots, 2)))

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
        tighten stop to lock in profits.
        """
        if not settings.TRAILING_STOP_ENABLED:
            return None

        trail_distance = atr * 1.2

        if position_type == "BUY":
            profit_points = current_price - entry_price
            if profit_points >= atr * settings.TRAILING_STOP_ACTIVATION_R:
                new_sl = round(current_price - trail_distance, 4)
                if new_sl > current_sl:
                    return new_sl
        elif position_type == "SELL":
            profit_points = entry_price - current_price
            if profit_points >= atr * settings.TRAILING_STOP_ACTIVATION_R:
                new_sl = round(current_price + trail_distance, 4)
                if new_sl < current_sl:
                    return new_sl

        return None

risk_manager = RiskManager()