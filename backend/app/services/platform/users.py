"""User management and authentication."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ConflictError, DomainError
from app.core.query import paginate
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


MIN_PASSWORD_LENGTH = 10


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise DomainError(
            "user.password_too_short", f"Passwords need at least {MIN_PASSWORD_LENGTH} characters"
        )


async def add_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    role: str,
    tenant_id: uuid.UUID | None,
) -> User:
    """Create a user through the API: operators need a tenant, names are unique."""
    _check_password(password)
    if role == "operator" and tenant_id is None:
        raise DomainError("user.tenant_required", "An operator belongs to a tenant")
    if await get_user_by_username(session, username) is not None:
        raise ConflictError("user.username_taken", f"User '{username}' exists")
    return await create_user(
        session, username=username, password=password, role=role, tenant_id=tenant_id
    )


async def list_users(
    session: AsyncSession, *, tenant_id: uuid.UUID | None, skip: int, limit: int
) -> tuple[list[User], int]:
    """Users, restricted to one tenant when ``tenant_id`` is given."""
    stmt = select(User).order_by(User.username)
    if tenant_id is not None:
        stmt = stmt.where(User.tenant_id == tenant_id)
    return await paginate(session, stmt, skip=skip, limit=limit)


async def _active_admins(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))
    )
    return int(result.scalar_one())


async def update_user(
    session: AsyncSession,
    user: User,
    *,
    password: str | None = None,
    is_active: bool | None = None,
    role: str | None = None,
    tenant_id: uuid.UUID | None | object = ...,
) -> User:
    """Reset a password, (de)activate, or change role and tenant. Keeps one active admin."""
    if password is not None:
        _check_password(password)
        user.password_hash = hash_password(password)
    new_role = role or user.role
    if role is not None and role not in ROLES:
        raise DomainError("user.unknown_role", f"Unknown role '{role}'")
    new_tenant = user.tenant_id if tenant_id is ... else tenant_id
    if new_role == "operator" and new_tenant is None:
        raise DomainError("user.tenant_required", "An operator belongs to a tenant")
    losing_admin = (
        user.role == "admin" and user.is_active and (new_role != "admin" or is_active is False)
    )
    if losing_admin and await _active_admins(session) <= 1:
        raise DomainError("user.last_admin", "The last active admin must stay active")
    user.role = new_role
    user.tenant_id = new_tenant  # type: ignore[assignment]
    if is_active is not None:
        user.is_active = is_active
    await session.flush()
    return user


async def change_own_password(session: AsyncSession, user: User, old: str, new: str) -> None:
    """Change the caller's own password after checking the old one."""
    if not verify_password(old, user.password_hash):
        raise AuthError("auth.invalid_credentials", "The current password is wrong")
    _check_password(new)
    user.password_hash = hash_password(new)
    await session.flush()
