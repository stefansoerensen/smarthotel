"""Tenants (Mandanten) and properties (Häuser)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_scoped_property, require_admin, tenant_scope
from app.models.estate.property import Property
from app.models.platform.user import User
from app.schemas.native.common import Page
from app.schemas.native.estate import (
    PropertyIn,
    PropertyOut,
    PropertyPatch,
    TenantIn,
    TenantOut,
    TenantPatch,
)
from app.services.estate import properties
from app.services.platform import tenants

router = APIRouter(tags=["estate"])


async def _out(db: AsyncSession, prop: Property) -> PropertyOut:
    tenant = await tenants.get_tenant_by_id(db, prop.tenant_id)
    return PropertyOut(
        code=prop.code,
        tenant_code=tenant.code,
        name=prop.name,
        time_zone=prop.time_zone,
        street=prop.street,
        postal_code=prop.postal_code,
        city=prop.city,
        country_code=prop.country_code,
    )


@router.get("/tenants", response_model=Page[TenantOut])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[TenantOut]:
    """Tenants the user may see: all for admins, their own for operators."""
    rows, total = await tenants.list_tenants(db, only_id=tenant_scope(user), skip=skip, limit=limit)
    return Page(items=[TenantOut.model_validate(t) for t in rows], total=total)


@router.post("/tenants", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantIn, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> TenantOut:
    """Create a tenant (admins only)."""
    tenant = await tenants.create_tenant(db, code=data.code, name=data.name)
    await db.commit()
    return TenantOut.model_validate(tenant)


@router.patch("/tenants/{tenant_code}", response_model=TenantOut)
async def patch_tenant(
    tenant_code: str,
    data: TenantPatch,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TenantOut:
    """Rename a tenant (admins only)."""
    tenant = await tenants.get_tenant(db, tenant_code)
    await tenants.rename_tenant(db, tenant, data.name)
    await db.commit()
    return TenantOut.model_validate(tenant)


@router.get("/properties", response_model=Page[PropertyOut])
async def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[PropertyOut]:
    """Properties the user may see."""
    rows, total = await properties.list_properties(
        db, tenant_id=tenant_scope(user), skip=skip, limit=limit
    )
    return Page(items=[await _out(db, p) for p in rows], total=total)


@router.post("/properties", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
async def create_property(
    data: PropertyIn, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> PropertyOut:
    """Create a property for a tenant (admins only)."""
    tenant = await tenants.get_tenant(db, data.tenant_code)
    prop = await properties.create_property(
        db,
        tenant_id=tenant.id,
        code=data.code,
        name=data.name,
        time_zone=data.time_zone,
        street=data.street,
        postal_code=data.postal_code,
        city=data.city,
        country_code=data.country_code,
    )
    out = await _out(db, prop)
    await db.commit()
    return out


@router.get("/properties/{property_code}", response_model=PropertyOut)
async def get_property(
    prop: Property = Depends(get_scoped_property), db: AsyncSession = Depends(get_db)
) -> PropertyOut:
    """One property."""
    return await _out(db, prop)


@router.patch("/properties/{property_code}", response_model=PropertyOut)
async def patch_property(
    data: PropertyPatch,
    prop: Property = Depends(get_scoped_property),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PropertyOut:
    """Change a property (admins only)."""
    await properties.update_property(db, prop, data.model_dump(exclude_unset=True))
    out = await _out(db, prop)
    await db.commit()
    return out
