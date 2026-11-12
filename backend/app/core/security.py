"""Password hashing and JWT handling."""

from datetime import timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import utcnow
from app.core.errors import AuthError

NATIVE_AUDIENCE = "native"


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(subject: str, *, role: str, expires_minutes: int | None = None) -> str:
    """Create a signed JWT for ``subject``."""
    now = utcnow()
    minutes = expires_minutes or settings.access_token_expire_minutes
    claims: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "aud": NATIVE_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT; raise AuthError when invalid."""
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=NATIVE_AUDIENCE,
        )
    except JWTError as exc:
        raise AuthError("auth.invalid_token", "Invalid or expired token") from exc
