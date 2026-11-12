"""The device registry: gateways and devices of a property.

Callers pass the property (loaded through ``services.estate.properties``); this module never reads
the estate tables itself.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.core.query import paginate
from app.models.devices.device import Device
from app.models.devices.gateway import Gateway
from app.services.devices import catalogue
from app.services.platform import events

if TYPE_CHECKING:
    from app.models.estate.property import Property

_DEVICE_EDITABLE = ("name", "kind", "protocol", "address", "location", "controllable")


def _entity(prop: Property, code: str) -> str:
    return f"{prop.code}/{code}"


def _check_kind_and_protocol(kind: str, protocol: str) -> None:
    if kind not in catalogue.DEVICE_KINDS:
        raise DomainError("device.unknown_kind", f"Unknown device kind '{kind}'")
    if protocol not in catalogue.PROTOCOLS:
        raise DomainError("device.unknown_protocol", f"Unknown protocol '{protocol}'")


def _safety_read_only() -> DomainError:
    return DomainError(
        "device.safety_read_only",
        "Safety devices are read only: the platform never controls fire protection or life safety",
    )


# ---------- gateways ----------


async def find_gateway(session: AsyncSession, prop: Property, code: str) -> Gateway | None:
    """Return the gateway ``code`` of ``prop`` or None."""
    result = await session.execute(
        select(Gateway).where(Gateway.property_id == prop.id, Gateway.code == code)
    )
    return result.scalar_one_or_none()


async def register_gateway(
    session: AsyncSession, prop: Property, *, code: str, name: str
) -> Gateway:
    """Register an edge gateway in ``prop``."""
    if await find_gateway(session, prop, code) is not None:
        raise ConflictError("gateway.code_taken", f"Gateway '{code}' exists in {prop.code}")
    gateway = Gateway(property_id=prop.id, code=code, name=name, status="provisioned")
    session.add(gateway)
    await session.flush()
    await events.emit(
        session,
        topic="gateway",
        event_type="registered",
        entity_code=_entity(prop, code),
        property_code=prop.code,
        payload={"name": name},
    )
    return gateway


async def list_gateways(session: AsyncSession, prop: Property) -> list[Gateway]:
    """All gateways of ``prop`` ordered by code."""
    result = await session.execute(
        select(Gateway).where(Gateway.property_id == prop.id).order_by(Gateway.code)
    )
    return list(result.scalars())


async def gateway_codes(session: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Map gateway ids to their codes."""
    if not ids:
        return {}
    result = await session.execute(select(Gateway.id, Gateway.code).where(Gateway.id.in_(ids)))
    return {row.id: row.code for row in result}


# ---------- devices ----------


async def _gateway_id(session: AsyncSession, prop: Property, code: str | None) -> uuid.UUID | None:
    if code is None:
        return None
    gateway = await find_gateway(session, prop, code)
    if gateway is None:
        raise NotFoundError("gateway", code)
    return gateway.id


async def register_device(
    session: AsyncSession,
    prop: Property,
    *,
    code: str,
    name: str,
    kind: str,
    protocol: str,
    address: str | None = None,
    location: str | None = None,
    gateway_code: str | None = None,
    controllable: bool | None = None,
) -> Device:
    """Register a device. Safety kinds are always read only; asking otherwise is an error.

    ``controllable`` defaults to ``True`` for ordinary kinds and ``False`` for safety kinds.
    """
    _check_kind_and_protocol(kind, protocol)
    safety = catalogue.is_safety(kind)
    if safety and controllable:
        raise _safety_read_only()
    existing = await session.execute(
        select(Device.id).where(Device.property_id == prop.id, Device.code == code)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("device.code_taken", f"Device '{code}' exists in {prop.code}")
    device = Device(
        property_id=prop.id,
        gateway_id=await _gateway_id(session, prop, gateway_code),
        code=code,
        name=name,
        kind=kind,
        protocol=protocol,
        address=address,
        location=location,
        controllable=False if safety else (True if controllable is None else controllable),
        status="active",
    )
    session.add(device)
    await session.flush()
    await events.emit(
        session,
        topic="device",
        event_type="registered",
        entity_code=_entity(prop, code),
        property_code=prop.code,
        payload={"kind": kind, "protocol": protocol, "location": location},
    )
    return device


async def get_device(session: AsyncSession, prop: Property, code: str) -> Device:
    """Return device ``code`` of ``prop`` or raise NotFoundError."""
    result = await session.execute(
        select(Device).where(Device.property_id == prop.id, Device.code == code)
    )
    device = result.scalar_one_or_none()
    if device is None:
        raise NotFoundError("device", code)
    return device


async def list_devices(
    session: AsyncSession,
    prop: Property,
    *,
    kind: str | None = None,
    gateway_code: str | None = None,
    location: str | None = None,
    include_retired: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Device], int]:
    """List devices of ``prop`` with optional filters; retired ones only on request."""
    stmt = select(Device).where(Device.property_id == prop.id)
    if not include_retired:
        stmt = stmt.where(Device.status != "retired")
    if kind is not None:
        stmt = stmt.where(Device.kind == kind)
    if location is not None:
        stmt = stmt.where(Device.location == location)
    if gateway_code is not None:
        gateway = await find_gateway(session, prop, gateway_code)
        if gateway is None:
            return [], 0
        stmt = stmt.where(Device.gateway_id == gateway.id)
    stmt = stmt.order_by(Device.location.nulls_last(), Device.code)
    return await paginate(session, stmt, skip=skip, limit=limit)


async def update_device(
    session: AsyncSession, prop: Property, device: Device, changes: dict[str, Any]
) -> Device:
    """Change a device. Turning it into a safety kind drops control; asking for control fails."""
    if "gateway_code" in changes:
        device.gateway_id = await _gateway_id(session, prop, changes["gateway_code"])
    kind = changes.get("kind") or device.kind
    protocol = changes.get("protocol") or device.protocol
    _check_kind_and_protocol(kind, protocol)
    if catalogue.is_safety(kind):
        if changes.get("controllable"):
            raise _safety_read_only()
        changes = {**changes, "controllable": False}
    changed = {
        k: v
        for k, v in changes.items()
        if k in _DEVICE_EDITABLE and v is not None and getattr(device, k) != v
    }
    for key, value in changed.items():
        setattr(device, key, value)
    if changed or "gateway_code" in changes:
        await session.flush()
        await events.emit(
            session,
            topic="device",
            event_type="changed",
            entity_code=_entity(prop, device.code),
            property_code=prop.code,
            payload={
                "fields": sorted(
                    set(changed) | ({"gateway"} if "gateway_code" in changes else set())
                )
            },
        )
    return device


async def retire_device(session: AsyncSession, prop: Property, device: Device) -> Device:
    """Take a device out of service. The row stays for history; nothing is deleted."""
    if device.status != "retired":
        device.status = "retired"
        device.controllable = False
        await session.flush()
        await events.emit(
            session,
            topic="device",
            event_type="retired",
            entity_code=_entity(prop, device.code),
            property_code=prop.code,
        )
    return device
