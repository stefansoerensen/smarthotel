"""Properties (Häuser)."""

import uuid
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.core.query import paginate
from app.models.estate.property import Property
from app.services.platform import events

_EDITABLE = ("name", "time_zone", "street", "postal_code", "city", "country_code")


def _check_time_zone(time_zone: str) -> None:
    try:
        ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise DomainError(
            "property.invalid_time_zone", f"Unknown time zone '{time_zone}'"
        ) from None


async def create_property(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    code: str,
    name: str,
    time_zone: str = "Europe/Berlin",
    street: str | None = None,
    postal_code: str | None = None,
    city: str | None = None,
    country_code: str = "DE",
) -> Property:
    """Create a property for a tenant; the code is unique across the platform."""
    code = code.strip().upper()
    _check_time_zone(time_zone)
    existing = await session.execute(select(Property.id).where(Property.code == code))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("property.code_taken", f"Property code '{code}' is taken")
    prop = Property(
        tenant_id=tenant_id,
        code=code,
        name=name,
        time_zone=time_zone,
        street=street,
        postal_code=postal_code,
        city=city,
        country_code=country_code.upper(),
    )
    session.add(prop)
    await session.flush()
    await events.emit(
        session,
        topic="property",
        event_type="created",
        entity_code=code,
        property_code=code,
        payload={"name": name},
    )
    return prop


async def get_property(
    session: AsyncSession, code: str, *, tenant_id: uuid.UUID | None = None
) -> Property:
    """Return a property by code, optionally only within one tenant.

    A property of another tenant is reported as not found, so its existence does not leak.
    """
    stmt = select(Property).where(Property.code == code.strip().upper())
    if tenant_id is not None:
        stmt = stmt.where(Property.tenant_id == tenant_id)
    prop = (await session.execute(stmt)).scalar_one_or_none()
    if prop is None:
        raise NotFoundError("property", code)
    return prop


async def list_properties(
    session: AsyncSession, *, tenant_id: uuid.UUID | None, skip: int, limit: int
) -> tuple[list[Property], int]:
    """List properties, restricted to one tenant when ``tenant_id`` is given."""
    stmt = select(Property).order_by(Property.code)
    if tenant_id is not None:
        stmt = stmt.where(Property.tenant_id == tenant_id)
    return await paginate(session, stmt, skip=skip, limit=limit)


async def update_property(
    session: AsyncSession, prop: Property, changes: dict[str, Any]
) -> Property:
    """Apply the editable fields in ``changes`` and record the change."""
    if "time_zone" in changes and changes["time_zone"] is not None:
        _check_time_zone(changes["time_zone"])
    changed = {k: v for k, v in changes.items() if k in _EDITABLE and getattr(prop, k) != v}
    for key, value in changed.items():
        setattr(prop, key, value)
    if changed:
        await session.flush()
        await events.emit(
            session,
            topic="property",
            event_type="changed",
            entity_code=prop.code,
            property_code=prop.code,
            payload={"fields": sorted(changed)},
        )
    return prop
