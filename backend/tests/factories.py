"""Builders for tests. Extend these instead of hand-rolling fixtures."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import FixedClock
from app.core.security import create_access_token
from app.models.platform.outbox_event import OutboxEvent
from app.models.platform.tenant import Tenant
from app.services.estate import properties
from app.services.platform import tenants, users

NOW = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)


def make_clock() -> FixedClock:
    """The fixed clock every test starts from."""
    return FixedClock(NOW)


def _suffix() -> str:
    return uuid.uuid4().hex[:6].upper()


async def create_tenant(session: AsyncSession, *, code: str | None = None) -> Tenant:
    """Create a tenant with a unique code."""
    return await tenants.create_tenant(
        session, code=code or f"T{_suffix()}", name="Test Hotelgruppe"
    )


async def create_property(
    session: AsyncSession, *, tenant: Tenant | None = None, code: str | None = None
) -> Any:
    """Create a property (and a tenant when none is given)."""
    owner = tenant or await create_tenant(session)
    return await properties.create_property(
        session, tenant_id=owner.id, code=code or f"H{_suffix()}", name="Testhaus"
    )


async def auth_headers(
    session: AsyncSession, *, role: str = "admin", tenant: Tenant | None = None
) -> dict[str, str]:
    """Create a user and return Bearer headers for it."""
    username = f"{role}-{_suffix().lower()}"
    await users.create_user(
        session,
        username=username,
        password="Secret123!",
        role=role,
        tenant_id=tenant.id if tenant else None,
    )
    token = create_access_token(username, role=role)
    return {"Authorization": f"Bearer {token}"}


async def events_of(session: AsyncSession, topic: str, entity_code: str) -> list[str]:
    """Return the event types recorded for an entity, oldest first."""
    rows = await session.execute(
        select(OutboxEvent.event_type)
        .where(OutboxEvent.topic == topic, OutboxEvent.entity_code == entity_code)
        .order_by(OutboxEvent.occurred_at, OutboxEvent.created_at)
    )
    return list(rows.scalars())
