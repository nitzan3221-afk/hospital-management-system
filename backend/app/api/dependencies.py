"""Dependency wiring (composition root for each request).

Routers declare what they need (a service, the current user, a permission) and FastAPI
builds it here. This is the only place that knows which concrete repository is used.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.asynchronous.database import AsyncDatabase

from app.core.audit import DENIED, audit
from app.core.config import Settings, get_settings
from app.domain.errors import AuthenticationError, PermissionDeniedError
from app.domain.models import AuthenticatedUser
from app.domain.permissions import Permission, has_permission
from app.repositories.base import UserRepository
from app.repositories.mongo_user_repository import MongoUserRepository
from app.services.auth_service import AuthService

_bearer = HTTPBearer(auto_error=False, description="Paste the access_token returned by /api/auth/login")


def get_db(request: Request) -> AsyncDatabase:
    return request.app.state.database.db


def get_user_repository(db: AsyncDatabase = Depends(get_db)) -> UserRepository:
    return MongoUserRepository(db)


def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(users, settings)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser:
    if credentials is None:
        raise AuthenticationError("Missing bearer token")
    return auth.authenticate_token(credentials.credentials)


def require_permission(permission: Permission) -> Callable[..., Awaitable[AuthenticatedUser]]:
    """Dependency factory: ``user = Depends(require_permission(Permission.RECORD_VITALS))``."""

    async def checker(request: Request, user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not has_permission(user.role, permission):
            audit(
                "permission_denied",
                DENIED,
                actor=user.username,
                role=user.role.value,
                permission=permission.value,
                method=request.method,
                path=request.url.path,
            )
            raise PermissionDeniedError(f"Role '{user.role.value}' is not allowed to {permission.value}")
        return user

    return checker
