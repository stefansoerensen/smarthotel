"""Tenants (Mandanten)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.query import paginate
from app.models.platform.tenant import Tenant
from app.services.platform import events


async def create_tenant(session: AsyncSession, *, code: str, name: str) -> Tenant:
    """Create a tenant with a unique code."""
    code = code.strip().upper()
    if await find_tenant(session, code) is not None:
        raise ConflictError("tenant.code_taken", f"Tenant code '{code}' is taken")
    tenant = Tenant(code=code, name=name, is_active=True)
    session.add(tenant)
    await session.flush()
    await events.emit(
        session,
        topic="tenant",
        event_type="created",
        entity_code=code,
        property_code=None,
        payload={"name": name},
    )
    return tenant


async def find_tenant(session: AsyncSession, code: str) -> Tenant | None:
    """Return the tenant with ``code`` or None."""
    result = await session.execute(select(Tenant).where(Tenant.code == code.strip().upper()))
    return result.scalar_one_or_none()


async def get_tenant(session: AsyncSession, code: str) -> Tenant:
    """Return the tenant with ``code`` or raise NotFoundError."""
    tenant = await find_tenant(session, code)
    if tenant is None:
        raise NotFoundError("tenant", code)
    return tenant


async def get_tenant_by_id(session: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    """Return the tenant with ``tenant_id`` or raise NotFoundError."""
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundError("tenant", tenant_id)
    return tenant


async def list_tenants(
    session: AsyncSession, *, only_id: uuid.UUID | None, skip: int, limit: int
) -> tuple[list[Tenant], int]:
    """List tenants, restricted to ``only_id`` when given."""
    stmt = select(Tenant).order_by(Tenant.code)
    if only_id is not None:
        stmt = stmt.where(Tenant.id == only_id)
    return await paginate(session, stmt, skip=skip, limit=limit)


async def rename_tenant(session: AsyncSession, tenant: Tenant, name: str) -> Tenant:
    """Change a tenant's display name; the code stays, it identifies the tenant."""
    if tenant.name != name:
        tenant.name = name
        await session.flush()
        await events.emit(
            session,
            topic="tenant",
            event_type="changed",
            entity_code=tenant.code,
            property_code=None,
            payload={"fields": ["name"]},
        )
    return tenant
