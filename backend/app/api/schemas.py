"""Request / response bodies of the HTTP API (separate from domain entities)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import Role
from app.domain.models import AuthenticatedUser
from app.domain.permissions import Permission, permissions_for


# ---------- Auth ----------

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, examples=["dr_house"])
    password: str = Field(min_length=1, examples=["password123"])


class UserResponse(BaseModel):
    username: str
    full_name: str
    role: Role
    permissions: list[Permission]

    @classmethod
    def from_user(cls, user: AuthenticatedUser) -> "UserResponse":
        return cls(
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            permissions=sorted(permissions_for(user.role), key=lambda p: p.value),
        )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse
