from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class RiskDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

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
