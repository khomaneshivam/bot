import time
from typing import Dict, Optional
from bot.risk.models import CircuitBreakerStatus

class CircuitBreakerManager:
    """
    Independent hard safety circuit breakers.
    Latches when risk thresholds are breached and halts new trades.
    Can only be reset via explicit privileged administrative intervention.
    """

    def __init__(self):
        self._tripped_breakers: Dict[str, str] = {}
        self._trip_timestamps: Dict[str, str] = {}

    def trip(self, breaker_name: str, reason: str) -> None:
        """Trips a circuit breaker and logs the event."""
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self._tripped_breakers[breaker_name] = reason
        self._trip_timestamps[breaker_name] = now
        print(f"[CIRCUIT_BREAKER] 🛑 Breaker '{breaker_name}' TRIPPED: {reason}")

    def reset_breaker(self, breaker_name: str) -> bool:
        """Resets an individual breaker."""
        if breaker_name in self._tripped_breakers:
            del self._tripped_breakers[breaker_name]
            if breaker_name in self._trip_timestamps:
                del self._trip_timestamps[breaker_name]
            print(f"[CIRCUIT_BREAKER] ✅ Breaker '{breaker_name}' RESET.")
            return True
        return False

    def reset_all(self) -> None:
        """Privileged administrative reset of all circuit breakers."""
        self._tripped_breakers.clear()
        self._trip_timestamps.clear()
        print("[CIRCUIT_BREAKER] ⚠️ All circuit breakers RESET by administrator.")

    def is_tripped(self) -> bool:
        """Returns True if any circuit breaker is active."""
        return len(self._tripped_breakers) > 0

    def get_status(self) -> CircuitBreakerStatus:
        return CircuitBreakerStatus(
            tripped=self.is_tripped(),
            active_breakers=dict(self._tripped_breakers),
            trip_timestamps=dict(self._trip_timestamps)
        )

circuit_breaker_manager = CircuitBreakerManager()
