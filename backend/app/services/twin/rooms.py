"""Rooms, their twin points, rollout of a room type, and the simulator applied to rooms."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, NotFoundError
from app.models.twin.room import Room, RoomPoint
from app.models.twin.room_type import RoomType
from app.services.devices import registry
from app.services.platform import events
from app.services.twin import simulator, templates

if TYPE_CHECKING:
    from app.models.estate.property import Property

MAX_ROLLOUT_ROOMS = 500


@dataclass
class RolloutResult:
    """What a rollout did."""

    rooms_created: int = 0
    rooms_unchanged: int = 0
    devices_created: int = 0
    conflicts: list[str] = field(default_factory=list)


def device_code(room_code: str, key: str) -> str:
    """The registry code of a room's device: ``<room>-<KEY>``."""
    return f"{room_code}-{key.upper().replace('_', '-')}"


def _entity(prop: Property, code: str) -> str:
    return f"{prop.code}/{code}"


async def find_room(session: AsyncSession, prop: Property, code: str) -> Room | None:
    """Return room ``code`` of ``prop`` or None."""
    result = await session.execute(
        select(Room).where(Room.property_id == prop.id, Room.code == code)
    )
    return result.scalar_one_or_none()


async def get_room(session: AsyncSession, prop: Property, code: str) -> Room:
    """Return room ``code`` of ``prop`` or raise NotFoundError."""
    room = await find_room(session, prop, code)
    if room is None:
        raise NotFoundError("room", code)
    return room


async def list_rooms(session: AsyncSession, prop: Property) -> list[Room]:
    """All active rooms of ``prop``, ordered by floor and code."""
    result = await session.execute(
        select(Room).where(Room.property_id == prop.id, Room.status == "active").order_by(Room.code)
    )
    return list(result.scalars())


async def points_of(session: AsyncSession, room_ids: list) -> dict:
    """Map room id → its points in display order."""
    if not room_ids:
        return {}
    result = await session.execute(
        select(RoomPoint)
        .where(RoomPoint.room_id.in_(room_ids))
        .order_by(RoomPoint.position, RoomPoint.key)
    )
    grouped: dict = {room_id: [] for room_id in room_ids}
    for point in result.scalars():
        grouped[point.room_id].append(point)
    return grouped


async def room_type_codes(session: AsyncSession, ids: set) -> dict:
    """Map room type ids to codes."""
    if not ids:
        return {}
    result = await session.execute(select(RoomType.id, RoomType.code).where(RoomType.id.in_(ids)))
    return {row.id: row.code for row in result}


async def rollout(
    session: AsyncSession,
    prop: Property,
    room_type: RoomType,
    room_codes: list[str],
    *,
    floor: str | None = None,
) -> RolloutResult:
    """Create rooms of ``room_type`` with one device and twin point per template point.

    Idempotent: existing rooms of the same type only get the points they lack. A room that already
    has another type is reported in ``conflicts`` and left alone.
    """
    codes = list(dict.fromkeys(code.strip() for code in room_codes if code.strip()))
    if len(codes) > MAX_ROLLOUT_ROOMS:
        raise DomainError(
            "twin.rollout_too_large", f"At most {MAX_ROLLOUT_ROOMS} rooms per rollout"
        )
    specs = [templates.spec_of(p) for p in await templates.list_points(session, room_type)]
    result = RolloutResult()
    for code in codes:
        room = await find_room(session, prop, code)
        if room is not None and room.room_type_id not in (None, room_type.id):
            result.conflicts.append(code)
            continue
        if room is None:
            room = Room(
                property_id=prop.id,
                room_type_id=room_type.id,
                code=code,
                name=f"Zimmer {code}",
                floor=floor,
                status="active",
            )
            session.add(room)
            await session.flush()
            await events.emit(
                session,
                topic="room",
                event_type="created",
                entity_code=_entity(prop, code),
                property_code=prop.code,
                payload={"room_type": room_type.code, "floor": floor},
            )
            result.rooms_created += 1
            existing_keys: set[str] = set()
        else:
            room.room_type_id = room_type.id
            existing_keys = {p.key for p in (await points_of(session, [room.id]))[room.id]}
            if existing_keys >= {s.key for s in specs}:
                result.rooms_unchanged += 1
        for position, spec in enumerate(specs):
            if spec.key in existing_keys:
                continue
            dev_code = device_code(code, spec.key)
            device = await registry.find_device(session, prop, dev_code)
            if device is None:
                device = await registry.register_device(
                    session,
                    prop,
                    code=dev_code,
                    name=f"{spec.label} {code}",
                    kind=spec.kind,
                    protocol=spec.protocol,
                    location=code,
                    controllable=spec.writable,
                )
                result.devices_created += 1
            session.add(
                RoomPoint(
                    room_id=room.id,
                    device_id=device.id,
                    key=spec.key,
                    label=spec.label,
                    kind=spec.kind,
                    unit=spec.unit,
                    writable=spec.writable,
                    position=position,
                )
            )
        await session.flush()
    return result


async def write_point(
    session: AsyncSession, room: Room, key: str, value: float, *, now: datetime, source: str
) -> RoomPoint:
    """Set a writable point's value in the twin. Commands to devices follow with the edge (SB2)."""
    point = await _point(session, room, key)
    if not point.writable:
        raise DomainError("twin.point_read_only", f"Point '{key}' is read only")
    _set(point, value, now=now, source=source)
    await session.flush()
    return point


async def _point(session: AsyncSession, room: Room, key: str) -> RoomPoint:
    point = next((p for p in (await points_of(session, [room.id]))[room.id] if p.key == key), None)
    if point is None:
        raise NotFoundError("room_point", key)
    return point


def _set(point: RoomPoint, value: float, *, now: datetime, source: str) -> None:
    point.value = value
    point.value_at = now
    point.source = source


async def simulate_inputs(
    session: AsyncSession,
    room: Room,
    *,
    window: bool | None,
    presence: bool | None,
    now: datetime,
) -> None:
    """Let the simulator open or close a window or mark the room occupied."""
    points = {p.key: p for p in (await points_of(session, [room.id]))[room.id]}
    for key, flag in (("window", window), ("presence", presence)):
        if flag is not None and key in points:
            _set(points[key], 1.0 if flag else 0.0, now=now, source="simulator")
    await session.flush()


async def simulate_step(
    session: AsyncSession, prop: Property, *, minutes: float, outdoor: float, now: datetime
) -> int:
    """Advance every room of ``prop`` that has a temperature point; returns the number of rooms."""
    rooms = await list_rooms(session, prop)
    grouped = await points_of(session, [r.id for r in rooms])
    simulated = 0
    for room in rooms:
        points = {p.key: p for p in grouped[room.id]}
        if "temperature" not in points:
            continue

        def value(key: str, default: float) -> float:
            point = points.get(key)
            return default if point is None or point.value is None else point.value

        state = simulator.RoomState(
            temperature=value("temperature", simulator.START_TEMPERATURE),
            setpoint=value("setpoint", simulator.START_SETPOINT),
            window=value("window", 0.0),
            presence=value("presence", 0.0),
            valve=value("valve", 0.0),
            heat_meter=value("heat_meter", 0.0),
        )
        after = simulator.step(state, minutes=minutes, outdoor=outdoor)
        for key, new in (
            ("temperature", after.temperature),
            ("valve", after.valve),
            ("heat_meter", after.heat_meter),
            ("setpoint", after.setpoint),
            ("window", after.window),
            ("presence", after.presence),
        ):
            point = points.get(key)
            if point is None:
                continue
            if key in ("setpoint", "window", "presence") and point.value is not None:
                continue
            _set(point, new, now=now, source="simulator")
        simulated += 1
    await session.flush()
    return simulated
