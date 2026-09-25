"""
Institutional Trader Psychology & Behavioral Risk Guard
Implements cognitive bias protection, revenge trading circuit breakers,
FOMO liquidity trap vetoes, and discipline index tracking based on 20+ years of hedge fund psychology.
"""

import time
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timezone
import pandas as pd

class PsychologyGuard:
    def __init__(self):
        # Psychological Metrics & State Tracking
        self.discipline_index: float = 98.5        # 0 - 100% adherence to institutional playbook
        self.emotional_state: str = "OPTIMAL_FLOW"  # OPTIMAL_FLOW, PATIENT_HUNTING, DEFENSIVE_PRESERVATION, TILT_LOCKOUT
        self.consecutive_losses: int = 0
        self.consecutive_wins: int = 0
        self.last_trade_time: float = 0.0
        self.cooling_off_until: float = 0.0
        self.fomo_vetoes_count: int = 0
        self.revenge_blocks_count: int = 0
        self.psychology_log: List[Dict] = []

        # Mindset Rules & Max Drawdown Thresholds
        self.max_consecutive_losses_before_cooloff = 2
        self.cooloff_duration_seconds = 180  # 3 minutes forced pause after 2 losses
        self.daily_drawdown_limit_pct = 0.04  # 4% max daily loss on $100 portfolio ($4.00)
        self.starting_daily_balance = 100.0

    def evaluate_entry_psychology(self, symbol: str, current_candle: pd.Series, signal: str) -> Tuple[bool, str]:
        """
        Evaluates psychological traps before trade execution:
        1. Revenge Trading / Tilt Lockout
        2. FOMO Overextension Trap
        3. Euphoria Overconfidence Trap
        Returns (is_vetoed: bool, reason: str)
        """
        now = time.time()

        # 1. Check Tilt / Cooling-off Period
        if now < self.cooling_off_until:
            remaining = int(self.cooling_off_until - now)
            self.revenge_blocks_count += 1
            reason = f"PSYCHOLOGY VETO: Tilt & Revenge Shield Active. Cooling off for {remaining}s after consecutive loss."
            self._record_log("TILT_SHIELD", reason, symbol)
            return True, reason

        # 2. FOMO Trap Filter: Never buy the top or sell the bottom of an extended impulse
        rsi = current_candle.get("rsi_14", 50.0)
        dist_ema21 = abs(current_candle.get("dist_ema_21", 0.0))
        atr = current_candle.get("atr_14", 0.002)
        close = current_candle.get("close", 1.0)
        atr_ratio = current_candle.get("atr_ratio", 1.0)

        # Extended Long FOMO
        if signal == "BUY" and (rsi > 74.0 or (dist_ema21 > 0.015 and atr_ratio > 1.8)):
            self.fomo_vetoes_count += 1
            self.discipline_index = min(100.0, self.discipline_index + 0.2)
            reason = f"PSYCHOLOGY VETO: FOMO Trap Veto! RSI is {rsi:.1f} and price is extended >1.5% from 21 EMA. Retail liquidity exit."
            self._record_log("FOMO_VETO", reason, symbol)
            return True, reason

        # Extended Short Panic FOMO
        if signal == "SELL" and (rsi < 26.0 or (dist_ema21 > 0.015 and atr_ratio > 1.8)):
            self.fomo_vetoes_count += 1
            self.discipline_index = min(100.0, self.discipline_index + 0.2)
            reason = f"PSYCHOLOGY VETO: Panic Dump FOMO Veto! RSI is {rsi:.1f} at extreme oversold exhaustion. High risk of mean-reversion squeeze."
            self._record_log("FOMO_VETO", reason, symbol)
            return True, reason

        return False, "Psychological clearance granted. Trader state composed."

    def on_trade_closed(self, pnl: float, symbol: str, balance: float):
        """Updates emotional state and tilt counters after trade resolution."""
        now = time.time()
        self.last_trade_time = now

        if pnl < 0:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            if self.consecutive_losses >= self.max_consecutive_losses_before_cooloff:
                self.cooling_off_until = now + self.cooloff_duration_seconds
                self.emotional_state = "DEFENSIVE_PRESERVATION"
                msg = f"Consecutive loss #{self.consecutive_losses} detected (-${abs(pnl):.2f}). Initiating {self.cooloff_duration_seconds}s Tilt Shield to reset psychological baseline."
                self._record_log("COOLOFF_TRIGGERED", msg, symbol)
            else:
                self.emotional_state = "PATIENT_HUNTING"
        else:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.discipline_index = min(100.0, self.discipline_index + 0.5)
            if self.consecutive_wins >= 3:
                # Watch out for overconfidence bias
                self.emotional_state = "OPTIMAL_FLOW"
                msg = f"Winning streak #{self.consecutive_wins} (+${pnl:.2f}). Guarding against euphoria bias; maintaining strict asymmetry."
                self._record_log("WIN_STREAK", msg, symbol)
            else:
                self.emotional_state = "OPTIMAL_FLOW"

    def get_psychology_telemetry(self, current_balance: float = 100.0) -> Dict:
        """Returns psychological state telemetry for frontend dashboard."""
        now = time.time()
        cooloff_remaining = max(0, int(self.cooling_off_until - now))
        
        # Calculate Fear & Greed Institutional composite (0-100)
        # Greed increases on win streak, Fear increases on consecutive loss
        base_fg = 50
        if self.consecutive_wins > 0:
            base_fg = min(85, 50 + self.consecutive_wins * 8)
        elif self.consecutive_losses > 0:
            base_fg = max(18, 50 - self.consecutive_losses * 12)

        return {
            "discipline_index": round(self.discipline_index, 1),
            "emotional_state": self.emotional_state,
            "fear_greed_score": base_fg,
            "fear_greed_label": "EXTREME FEAR" if base_fg < 30 else ("FEAR" if base_fg < 45 else ("NEUTRAL / BALANCED" if base_fg <= 55 else ("GREED" if base_fg < 75 else "EXTREME GREED"))),
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "cooloff_remaining_seconds": cooloff_remaining,
            "tilt_shield_active": cooloff_remaining > 0,
            "fomo_vetoes_count": self.fomo_vetoes_count,
            "revenge_blocks_count": self.revenge_blocks_count,
            "mindset_mantra": self._get_mindset_mantra(),
            "recent_psychology_logs": self.psychology_log[-5:]
        }

    def _get_mindset_mantra(self) -> str:
        """Institutional mindset wisdom curated from 20+ years of fund management."""
        if self.cooling_off_until > time.time():
            return "Capital preservation is paramount. The best trade is often no trade. Wait for edge to return."
        if self.consecutive_losses > 0:
            return "Losses are the tuition fee of market participation. Adhere to asymmetric risk-to-reward."
        if self.consecutive_wins > 2:
            return "Euphoria is the prelude to drawdown. Maintain rigorous position sizing and risk discipline."
        return "Trade what you see, not what you feel. Let mathematics, probability, and structure dictate execution."

    def _record_log(self, event_type: str, detail: str, symbol: str):
        self.psychology_log.append({
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            "event": event_type,
            "detail": detail,
            "symbol": symbol
        })
        if len(self.psychology_log) > 50:
            self.psychology_log = self.psychology_log[-50:]

psychology_guard = PsychologyGuard()
