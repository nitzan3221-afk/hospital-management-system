"""Authentication: verify credentials, issue and validate access tokens."""

from dataclasses import dataclass
from datetime import datetime

from app.core.audit import FAILURE, audit
from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.domain.enums import Role
from app.domain.errors import AuthenticationError
from app.domain.models import AuthenticatedUser
from app.repositories.base import UserRepository

_INVALID_CREDENTIALS = "Invalid username or password"


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    expires_at: datetime
    user: AuthenticatedUser


class AuthService:
    # Used to spend the same bcrypt time when the username does not exist, so response
    # timing does not reveal which usernames are valid.
    _dummy_hash: str | None = None

    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self._users = users
        self._settings = settings

    async def login(self, username: str, password: str) -> LoginResult:
        user = await self._users.get_by_username(username)

        if user is None:
            verify_password(password, self._get_dummy_hash())
            audit("login", FAILURE, actor=username, reason="unknown_user")
            raise AuthenticationError(_INVALID_CREDENTIALS)

        if not verify_password(password, user.password_hash):
            audit("login", FAILURE, actor=username, role=user.role.value, reason="wrong_password")
            raise AuthenticationError(_INVALID_CREDENTIALS)

        token, expires_at = create_access_token(
            {"sub": user.username, "name": user.full_name, "role": user.role.value},
            secret=self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
            expires_minutes=self._settings.jwt_expire_minutes,
        )
        audit("login", actor=user.username, role=user.role.value)
        return LoginResult(
            access_token=token,
            expires_at=expires_at,
            user=AuthenticatedUser(username=user.username, full_name=user.full_name, role=user.role),
        )

    def authenticate_token(self, token: str) -> AuthenticatedUser:
        """Resolve a bearer token to the user it was issued to (stateless: no DB lookup)."""
        try:
            claims = decode_access_token(
                token, secret=self._settings.jwt_secret, algorithm=self._settings.jwt_algorithm
            )
            return AuthenticatedUser(username=claims["sub"], full_name=claims["name"], role=Role(claims["role"]))
        except AuthenticationError as exc:
            audit("token_rejected", FAILURE, reason=str(exc))
            raise
        except (KeyError, ValueError) as exc:
            audit("token_rejected", FAILURE, reason="malformed_claims")
            raise AuthenticationError("Invalid token") from exc

    @classmethod
    def _get_dummy_hash(cls) -> str:
        if cls._dummy_hash is None:
            cls._dummy_hash = hash_password("dummy-password-for-timing")
        return cls._dummy_hash
