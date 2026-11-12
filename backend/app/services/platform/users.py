"""User management and authentication."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, DomainError
from app.core.security import hash_password, verify_password
from app.models.platform.user import ROLES, User


async def create_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    role: str,
    tenant_id: uuid.UUID | None = None,
) -> User:
    """Create a user with a hashed password."""
    if role not in ROLES:
        raise DomainError("user.unknown_role", f"Unknown role '{role}'")
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        tenant_id=tenant_id,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    """Return the user with ``username`` or None."""
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate(session: AsyncSession, username: str, password: str) -> User:
    """Return the active user for valid credentials, else raise AuthError."""
    user = await get_user_by_username(session, username)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthError("auth.invalid_credentials", "Invalid username or password")
    return user
