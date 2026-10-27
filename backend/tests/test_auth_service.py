"""Login and token validation."""

import pytest

from app.core.config import Settings
from app.domain.enums import Role
from app.domain.errors import AuthenticationError
from app.seed import DEMO_PASSWORD, build_users
from app.services.auth_service import AuthService
from tests.fakes import InMemoryUserRepository


@pytest.fixture
def auth_service() -> AuthService:
    settings = Settings(jwt_secret="test-secret-that-is-at-least-32-bytes-long")
    return AuthService(InMemoryUserRepository(build_users()), settings)


async def test_login_success_returns_token_for_user_role(auth_service: AuthService, audit_log) -> None:
    result = await auth_service.login("nurse_joy", DEMO_PASSWORD)

    user = auth_service.authenticate_token(result.access_token)
    assert user.username == "nurse_joy"
    assert user.role == Role.NURSE
    assert ("login", "success") in audit_log.events()


@pytest.mark.parametrize("username,password", [("nurse_joy", "wrong"), ("nobody", DEMO_PASSWORD)])
async def test_login_failure_is_rejected_and_audited(auth_service: AuthService, audit_log, username, password) -> None:
    with pytest.raises(AuthenticationError):
        await auth_service.login(username, password)

    assert ("login", "failure") in audit_log.events()


async def test_tampered_token_is_rejected(auth_service: AuthService) -> None:
    result = await auth_service.login("dr_house", DEMO_PASSWORD)
    header, payload, signature = result.access_token.split(".")
    tampered = f"{header}.{payload}.{signature[::-1]}"

    with pytest.raises(AuthenticationError):
        auth_service.authenticate_token(tampered)
