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

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8)
    confirm_password: Optional[str] = None
    role: Optional[str] = "TRADER"
    admin_key: Optional[str] = None

class RegisterResponse(BaseModel):
    success: bool = True
    message: str = "Account successfully registered."
    access_token: str
    token_type: str = "Bearer"
    role: Role
    user_id: str
    username: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: Optional[str] = None

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
