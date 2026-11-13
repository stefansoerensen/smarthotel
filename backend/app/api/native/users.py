"""User management (admins) and the caller's own password."""

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_admin, tenant_scope
from app.core.errors import NotFoundError
from app.models.platform.user import User
from app.schemas.native.common import Page
from app.services.platform import tenants, users

router = APIRouter(tags=["users"])


class UserIn(BaseModel):
    """A new user."""

    username: str = Field(min_length=2, max_length=100, pattern=r"^[A-Za-z0-9_.@-]+$")
    password: str = Field(min_length=1, max_length=200)
    role: str = Field(pattern=r"^(admin|operator)$")
    tenant_code: str | None = None


class UserPatch(BaseModel):
    """Changes to a user; omitted fields stay."""

    password: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None
    role: str | None = Field(default=None, pattern=r"^(admin|operator)$")
    tenant_code: str | None = None


class UserListOut(BaseModel):
    """A user as admins see it."""

    username: str
    role: str
    tenant_code: str | None
    is_active: bool


class PasswordIn(BaseModel):
    """Change the own password."""

    old_password: str
    new_password: str = Field(max_length=200)


async def _out(db: AsyncSession, user: User) -> UserListOut:
    code = None
    if user.tenant_id is not None:
        code = (await tenants.get_tenant_by_id(db, user.tenant_id)).code
    return UserListOut(
        username=user.username, role=user.role, tenant_code=code, is_active=user.is_active
    )


@router.get("/users", response_model=Page[UserListOut])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[UserListOut]:
    """All users for admins; the users of their own tenant for operators."""
    rows, total = await users.list_users(db, tenant_id=tenant_scope(user), skip=skip, limit=limit)
    return Page(items=[await _out(db, u) for u in rows], total=total)


@router.post("/users", response_model=UserListOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserIn, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> UserListOut:
    """Create a user (admins only)."""
    tenant_id = (await tenants.get_tenant(db, data.tenant_code)).id if data.tenant_code else None
    user = await users.add_user(
        db, username=data.username, password=data.password, role=data.role, tenant_id=tenant_id
    )
    out = await _out(db, user)
    await db.commit()
    return out


@router.patch("/users/{username}", response_model=UserListOut)
async def patch_user(
    username: str,
    data: UserPatch,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListOut:
    """Reset a password, (de)activate, or change role and tenant (admins only)."""
    user = await users.get_user_by_username(db, username)
    if user is None:
        raise NotFoundError("user", username)
    changes = data.model_dump(exclude_unset=True)
    kwargs: dict = {
        "password": changes.get("password"),
        "is_active": changes.get("is_active"),
        "role": changes.get("role"),
    }
    if "tenant_code" in changes:
        code = changes["tenant_code"]
        kwargs["tenant_id"] = (await tenants.get_tenant(db, code)).id if code else None
    await users.update_user(db, user, **kwargs)
    out = await _out(db, user)
    await db.commit()
    return out


@router.post("/auth/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: PasswordIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    """Change the caller's own password."""
    await users.change_own_password(db, user, data.old_password, data.new_password)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
