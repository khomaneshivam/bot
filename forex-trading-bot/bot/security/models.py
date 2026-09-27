from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class Role(str, Enum):
    READ_ONLY = "READ_ONLY"
    TRADER = "TRADER"
    ADMIN = "ADMIN"

    def can_access(self, required_role: "Role") -> bool:
        hierarchy = {
            Role.READ_ONLY: 1,
            Role.TRADER: 2,
            Role.ADMIN: 3
        }
        return hierarchy[self] >= hierarchy[required_role]

class User(BaseModel):
    id: str
    username: str
    role: Role
    is_active: bool = True
    created_at: Optional[str] = None
    last_login: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    role: Role
    user_id: str
    username: str

class AuditRecord(BaseModel):
    event_id: str
    timestamp: str
    actor_id: str
    actor_role: str
    action: str
    target: str
    old_val: Optional[str] = None
    new_val: Optional[str] = None
    result: str
    client_ip: Optional[str] = None
    correlation_id: Optional[str] = None
