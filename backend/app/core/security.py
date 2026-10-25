"""Password hashing (bcrypt) and access tokens (JWT)."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.domain.errors import AuthenticationError


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:  # malformed hash
        return False


def create_access_token(
    claims: dict[str, Any], *, secret: str, algorithm: str, expires_minutes: int
) -> tuple[str, datetime]:
    """Return a signed JWT containing ``claims`` plus issued-at / expiry, and the expiry time."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expires_minutes)
    payload = {**claims, "iat": now, "exp": expires_at}
    return jwt.encode(payload, secret, algorithm=algorithm), expires_at


def decode_access_token(token: str, *, secret: str, algorithm: str) -> dict[str, Any]:
    """Verify signature and expiry. Raises ``AuthenticationError`` if the token is invalid."""
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid token") from exc
