"""FastAPI dependencies shared by all routers."""

import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, SystemClock
from app.core.database import SessionLocal
from app.core.errors import AuthError
from app.core.security import decode_access_token
from app.models.estate.property import Property
from app.models.platform.user import User
from app.services.estate import properties
from app.services.platform import users

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a session; route handlers commit explicitly, anything else is rolled back."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_clock() -> Clock:
    """Provide the wall clock; tests override this dependency."""
    return SystemClock()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the user from a native Bearer JWT."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = decode_access_token(credentials.credentials)
    except AuthError:
        raise unauthorized from None
    user = await users.get_user_by_username(db, str(claims.get("sub")))
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Allow only admin users."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def tenant_scope(user: User) -> uuid.UUID | None:
    """The tenant a user is limited to; ``None`` means every tenant (admins).

    An operator without a tenant is limited to a tenant id that matches nothing.
    """
    if user.role == "admin":
        return None
    return user.tenant_id or uuid.UUID(int=0)


async def get_scoped_property(
    property_code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Property:
    """Load the property in the path, as seen by the current user (404 outside their tenant)."""
    return await properties.get_property(db, property_code, tenant_id=tenant_scope(user))
