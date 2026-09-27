from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class RiskDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class SizedVolume(float):
    """
    Float representing position size (volume/lot).
    Supports 2-tuple unpacking (volume, metrics) for backwards and forwards compatibility:
      size = risk_manager.calculate_position_size(...)
      if size > 0: ...
    and:
      vol, metrics = risk_manager.calculate_position_size(...)
    """
    metrics: Dict[str, Any]

    def __new__(cls, volume: float, metrics: Optional[Dict[str, Any]] = None):
        instance = super().__new__(cls, float(volume))
        instance.metrics = metrics or {}
        return instance

    def __iter__(self):
        yield float(self)
        yield self.metrics

    def __getitem__(self, index):
        if index == 0:
            return float(self)
        elif index == 1:
            return self.metrics
        raise IndexError("SizedVolume index out of range (0 or 1)")

class RiskCheckResult(BaseModel):
    decision: RiskDecision
    approved: bool
    recommended_size: float = 0.0
    passed_gates: List[str] = Field(default_factory=list)
    failed_gates: List[str] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
    details: Dict[str, str] = Field(default_factory=dict)

class CircuitBreakerStatus(BaseModel):
    tripped: bool
    active_breakers: Dict[str, str] = Field(default_factory=dict)
    trip_timestamps: Dict[str, str] = Field(default_factory=dict)
