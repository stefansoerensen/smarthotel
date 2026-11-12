"""Room types (templates) and their data points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.models.twin.room_type import RoomType, RoomTypePoint
from app.services.devices import catalogue
from app.services.platform import events

if TYPE_CHECKING:
    from app.models.estate.property import Property


@dataclass(frozen=True)
class PointSpec:
    """A data point as it is defined in a template."""

    key: str
    label: str
    kind: str
    protocol: str
    unit: str | None
    writable: bool


STANDARD_POINTS: tuple[PointSpec, ...] = (
    PointSpec("temperature", "Raumtemperatur", "temperature_sensor", "knx", "°C", False),
    PointSpec("setpoint", "Sollwert", "thermostat", "knx", "°C", True),
    PointSpec("window", "Fenster", "window_contact", "knx", None, False),
    PointSpec("presence", "Präsenz", "presence_sensor", "knx", None, False),
    PointSpec("valve", "Heizventil", "valve", "knx", "%", True),
    PointSpec("light", "Licht", "light", "knx", None, True),
    PointSpec("heat_meter", "Wärmezähler", "meter", "modbus", "kWh", False),
)


def check_point(spec: PointSpec) -> None:
    """Validate a point: known kind and protocol, and writable only where the kind allows it."""
    if spec.kind not in catalogue.DEVICE_KINDS:
        raise DomainError("device.unknown_kind", f"Unknown device kind '{spec.kind}'")
    if spec.protocol not in catalogue.PROTOCOLS:
        raise DomainError("device.unknown_protocol", f"Unknown protocol '{spec.protocol}'")
    if spec.writable and not catalogue.can_write(spec.kind):
        raise DomainError(
            "twin.point_read_only",
            f"Points of kind '{spec.kind}' are measured or safety related and cannot be written",
        )


def _entity(prop: Property, code: str) -> str:
    return f"{prop.code}/{code}"


async def find_room_type(session: AsyncSession, prop: Property, code: str) -> RoomType | None:
    """Return room type ``code`` of ``prop`` or None."""
    result = await session.execute(
        select(RoomType).where(RoomType.property_id == prop.id, RoomType.code == code.upper())
    )
    return result.scalar_one_or_none()


async def get_room_type(session: AsyncSession, prop: Property, code: str) -> RoomType:
    """Return room type ``code`` of ``prop`` or raise NotFoundError."""
    room_type = await find_room_type(session, prop, code)
    if room_type is None:
        raise NotFoundError("room_type", code)
    return room_type


async def list_points(session: AsyncSession, room_type: RoomType) -> list[RoomTypePoint]:
    """The points of a room type in display order."""
    result = await session.execute(
        select(RoomTypePoint)
        .where(RoomTypePoint.room_type_id == room_type.id)
        .order_by(RoomTypePoint.position, RoomTypePoint.key)
    )
    return list(result.scalars())


async def list_room_types(session: AsyncSession, prop: Property) -> list[RoomType]:
    """All room types of ``prop`` ordered by code."""
    result = await session.execute(
        select(RoomType).where(RoomType.property_id == prop.id).order_by(RoomType.code)
    )
    return list(result.scalars())


async def _add(session: AsyncSession, room_type: RoomType, spec: PointSpec, position: int) -> None:
    session.add(
        RoomTypePoint(
            room_type_id=room_type.id,
            key=spec.key,
            label=spec.label,
            kind=spec.kind,
            protocol=spec.protocol,
            unit=spec.unit,
            writable=spec.writable,
            position=position,
        )
    )


async def create_room_type(
    session: AsyncSession,
    prop: Property,
    *,
    code: str,
    name: str,
    description: str | None = None,
    standard_points: bool = False,
) -> RoomType:
    """Create a room type, optionally filled with the standard points."""
    code = code.strip().upper()
    if await find_room_type(session, prop, code) is not None:
        raise ConflictError("room_type.code_taken", f"Room type '{code}' exists in {prop.code}")
    room_type = RoomType(property_id=prop.id, code=code, name=name, description=description)
    session.add(room_type)
    await session.flush()
    if standard_points:
        for position, spec in enumerate(STANDARD_POINTS):
            await _add(session, room_type, spec, position)
        await session.flush()
    await events.emit(
        session,
        topic="room_type",
        event_type="created",
        entity_code=_entity(prop, code),
        property_code=prop.code,
        payload={"name": name, "standard_points": standard_points},
    )
    return room_type


async def update_room_type(
    session: AsyncSession,
    prop: Property,
    room_type: RoomType,
    *,
    name: str,
    description: str | None,
) -> RoomType:
    """Rename a room type or change its description."""
    if (room_type.name, room_type.description) != (name, description):
        room_type.name = name
        room_type.description = description
        await session.flush()
        await events.emit(
            session,
            topic="room_type",
            event_type="changed",
            entity_code=_entity(prop, room_type.code),
            property_code=prop.code,
            payload={"fields": ["name", "description"]},
        )
    return room_type


async def add_point(
    session: AsyncSession, prop: Property, room_type: RoomType, spec: PointSpec
) -> None:
    """Add a data point to a room type. Rooms already rolled out get it on the next rollout."""
    check_point(spec)
    points = await list_points(session, room_type)
    if any(p.key == spec.key for p in points):
        raise ConflictError("room_type.point_exists", f"Point '{spec.key}' exists")
    await _add(session, room_type, spec, max((p.position for p in points), default=-1) + 1)
    await session.flush()
    await events.emit(
        session,
        topic="room_type",
        event_type="changed",
        entity_code=_entity(prop, room_type.code),
        property_code=prop.code,
        payload={"point_added": spec.key},
    )


async def remove_point(
    session: AsyncSession, prop: Property, room_type: RoomType, key: str
) -> None:
    """Remove a point from the template; rooms already rolled out keep theirs."""
    points = await list_points(session, room_type)
    point = next((p for p in points if p.key == key), None)
    if point is None:
        raise NotFoundError("room_type_point", key)
    await session.delete(point)
    await session.flush()
    await events.emit(
        session,
        topic="room_type",
        event_type="changed",
        entity_code=_entity(prop, room_type.code),
        property_code=prop.code,
        payload={"point_removed": key},
    )


def spec_of(point: RoomTypePoint) -> PointSpec:
    """The spec of a stored template point."""
    return PointSpec(point.key, point.label, point.kind, point.protocol, point.unit, point.writable)
