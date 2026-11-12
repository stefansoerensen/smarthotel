"""Login and current-user endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.models.platform.user import User
from app.schemas.native.auth import LoginRequest, TokenResponse, UserOut
from app.services.platform import tenants, users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Exchange username/password for a JWT (rate limited per client IP)."""
    client_ip = request.client.host if request.client else "unknown"
    if not request.app.state.login_limiter.hit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts"
        )
    user = await users.authenticate(db, data.username, data.password)
    token = create_access_token(user.username, role=user.role)
    return TokenResponse(access_token=token, expires_in=settings.access_token_expire_minutes * 60)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UserOut:
    """Return the authenticated user."""
    tenant_code = None
    if user.tenant_id is not None:
        tenant_code = (await tenants.get_tenant_by_id(db, user.tenant_id)).code
    return UserOut(username=user.username, role=user.role, tenant_code=tenant_code)
