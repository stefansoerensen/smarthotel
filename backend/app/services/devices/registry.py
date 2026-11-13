"""The device registry: gateways and devices of a property.

Callers pass the property (loaded through ``services.estate.properties``); this module never reads
the estate tables itself.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
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


async def find_device(session: AsyncSession, prop: Property, code: str) -> Device | None:
    """Return device ``code`` of ``prop`` or None."""
    result = await session.execute(
        select(Device).where(Device.property_id == prop.id, Device.code == code)
    )
    return result.scalar_one_or_none()


async def device_codes(session: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Map device ids to their codes."""
    if not ids:
        return {}
    result = await session.execute(select(Device.id, Device.code).where(Device.id.in_(ids)))
    return {row.id: row.code for row in result}


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
    problem = (
        catalogue.check_address(protocol, changes["address"]) if changes.get("address") else None
    )
    if problem:
        raise DomainError("device.invalid_address", problem)
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


# ---------- gateways as edge clients (ADR-0006) ----------

GATEWAY_OFFLINE_AFTER = timedelta(minutes=2)


def hash_token(token: str) -> str:
    """SHA-256 of a gateway token, as stored."""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_gateway_token(session: AsyncSession, gateway: Gateway, *, now: datetime) -> str:
    """Create a new token for ``gateway``; the previous one stops working. Returned once."""
    token = secrets.token_urlsafe(32)
    gateway.token_hash = hash_token(token)
    gateway.provisioned_at = now
    await session.flush()
    return token


async def gateway_for_token(session: AsyncSession, token: str) -> Gateway | None:
    """The gateway that owns ``token``, or None."""
    result = await session.execute(select(Gateway).where(Gateway.token_hash == hash_token(token)))
    gateway = result.scalar_one_or_none()
    if gateway is None or gateway.status == "retired":
        return None
    return gateway


def gateway_status(gateway: Gateway, now: datetime) -> str:
    """``provisioned`` before the first heartbeat, then ``online`` or ``offline`` by last contact."""
    if gateway.status == "retired":
        return "retired"
    if gateway.last_seen_at is None:
        return "provisioned"
    return "online" if now - gateway.last_seen_at <= GATEWAY_OFFLINE_AFTER else "offline"


async def gateway_devices(session: AsyncSession, gateway: Gateway) -> list[Device]:
    """Active devices behind ``gateway``."""
    result = await session.execute(
        select(Device)
        .where(Device.gateway_id == gateway.id, Device.status != "retired")
        .order_by(Device.code)
    )
    return list(result.scalars())


async def record_heartbeat(
    session: AsyncSession, gateway: Gateway, health: dict[str, bool], *, now: datetime
) -> None:
    """Mark the gateway seen and store the health it reports for its devices."""
    gateway.last_seen_at = now
    gateway.status = "online"
    for device in await gateway_devices(session, gateway):
        if device.code in health:
            device.health = "ok" if health[device.code] else "fault"
            device.last_seen_at = now
    await session.flush()


async def gateways_of_devices(
    session: AsyncSession, device_ids: set[uuid.UUID]
) -> dict[uuid.UUID, uuid.UUID]:
    """Map device ids to the id of the gateway they sit behind (devices without one are left out)."""
    if not device_ids:
        return {}
    result = await session.execute(
        select(Device.id, Device.gateway_id).where(
            Device.id.in_(device_ids), Device.gateway_id.is_not(None)
        )
    )
    return {row.id: row.gateway_id for row in result}


async def get_device_by_id(session: AsyncSession, device_id: uuid.UUID) -> Device:
    """Load a device by id."""
    device = await session.get(Device, device_id)
    if device is None:
        raise NotFoundError("device", device_id)
    return device
