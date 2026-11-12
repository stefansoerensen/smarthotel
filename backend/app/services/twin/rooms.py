"""Rooms, their twin points, rollout of a room type, and the simulator applied to rooms."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, NotFoundError
from app.models.twin.history import MeterReading, OccupancyPeriod
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
    gateway_code: str | None = None,
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
    if (
        gateway_code is not None
        and await registry.find_gateway(session, prop, gateway_code) is None
    ):
        raise NotFoundError("gateway", gateway_code)
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
                    gateway_code=gateway_code,
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
) -> tuple[RoomPoint, bool]:
    """Set a writable point. Returns the point and whether its device sits behind a gateway.

    Behind a gateway the value becomes *desired* until the gateway reports it; the caller then
    queues a command (ADR-0006). Without a gateway the twin takes the value directly.
    """
    point = await _point(session, room, key)
    if not point.writable:
        raise DomainError("twin.point_read_only", f"Point '{key}' is read only")
    behind_gateway = bool(
        point.device_id and await registry.gateways_of_devices(session, {point.device_id})
    )
    if behind_gateway:
        point.desired = value
        point.desired_at = now
    else:
        _set(point, value, now=now, source=source)
    await session.flush()
    return point, behind_gateway


async def edge_room_ids(session: AsyncSession, room_ids: list) -> set:
    """Rooms with at least one device behind a gateway: the edge owns them, not the cloud simulator."""
    grouped = await points_of(session, room_ids)
    device_ids = {p.device_id for pts in grouped.values() for p in pts if p.device_id}
    with_gateway = set(await registry.gateways_of_devices(session, device_ids))
    return {
        room_id for room_id, pts in grouped.items() if any(p.device_id in with_gateway for p in pts)
    }


async def room_gateway_codes(session: AsyncSession, prop: Property, room_ids: list) -> dict:
    """Map room id → code of the gateway its devices sit behind (first one found)."""
    grouped = await points_of(session, room_ids)
    device_ids = {p.device_id for pts in grouped.values() for p in pts if p.device_id}
    by_device = await registry.gateways_of_devices(session, device_ids)
    codes = {g.id: g.code for g in await registry.list_gateways(session, prop)}
    result: dict = {}
    for room_id, pts in grouped.items():
        for p in pts:
            if p.device_id in by_device:
                result[room_id] = codes.get(by_device[p.device_id])
                break
    return result


async def apply_reading(
    session: AsyncSession, device_id, value: float, measured_at: datetime
) -> bool:
    """Store a gateway's reading on the twin point of ``device_id`` if it is newer than the last.

    Returns False when no point belongs to the device or the reading is not newer. A reading that
    matches the desired value clears it.
    """
    result = await session.execute(select(RoomPoint).where(RoomPoint.device_id == device_id))
    point = result.scalars().first()
    if point is None:
        return False
    if point.value_at is not None and measured_at <= point.value_at:
        return False
    _set(point, value, now=measured_at, source="edge")
    _record_meter(session, point, value, measured_at, "edge")
    if point.desired is not None and abs(point.desired - value) < 0.01:
        point.desired = None
        point.desired_at = None
    await session.flush()
    return True


async def _point(session: AsyncSession, room: Room, key: str) -> RoomPoint:
    point = next((p for p in (await points_of(session, [room.id]))[room.id] if p.key == key), None)
    if point is None:
        raise NotFoundError("room_point", key)
    return point


def _record_meter(
    session: AsyncSession, point: RoomPoint, value: float, at: datetime, source: str
) -> None:
    """Keep the history of meter points; other points keep only their last value."""
    if point.kind == "meter":
        session.add(
            MeterReading(
                room_point_id=point.id,
                room_id=point.room_id,
                value=value,
                measured_at=at,
                source=source,
            )
        )


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
    if room.id in await edge_room_ids(session, [room.id]):
        raise DomainError(
            "twin.edge_room", f"Room '{room.code}' is run by its gateway, not the cloud simulator"
        )
    points = {p.key: p for p in (await points_of(session, [room.id]))[room.id]}
    for key, flag in (("window", window), ("presence", presence)):
        if flag is not None and key in points:
            _set(points[key], 1.0 if flag else 0.0, now=now, source="simulator")
    await session.flush()


async def simulate_step(
    session: AsyncSession, prop: Property, *, minutes: float, outdoor: float, now: datetime
) -> int:
    """Advance every room of ``prop`` that has a temperature point; returns the number of rooms."""
    edge_rooms = await edge_room_ids(session, [r.id for r in await list_rooms(session, prop)])
    rooms = [r for r in await list_rooms(session, prop) if r.id not in edge_rooms]
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
            _record_meter(session, point, new, now, "simulator")
        simulated += 1
    await session.flush()
    return simulated


MODES = ("eco", "preheat", "comfort")
OCCUPANCIES = ("vacant", "arriving", "occupied")


async def apply_mode(
    session: AsyncSession,
    prop: Property,
    room: Room,
    *,
    occupancy: str,
    mode: str,
    reservation_code: str | None,
    setpoint: float,
    now: datetime,
) -> tuple[bool, RoomPoint | None, bool]:
    """Set a room's occupancy and mode; on a mode change write the mode's set point.

    Returns (mode changed, set point written, whether that point sits behind a gateway). The set
    point is written only on a change, so a guest's own adjustment stays until the next change.
    """
    await _track_occupancy(session, room, occupancy, reservation_code, now)
    room.occupancy = occupancy
    room.reservation_code = reservation_code
    if room.mode == mode:
        await session.flush()
        return False, None, False
    previous = room.mode
    room.mode = mode
    room.mode_since = now
    await events.emit(
        session,
        topic="room",
        event_type="mode_changed",
        entity_code=_entity(prop, room.code),
        property_code=prop.code,
        payload={"from": previous, "to": mode, "occupancy": occupancy},
    )
    points = {p.key: p for p in (await points_of(session, [room.id]))[room.id]}
    if "setpoint" not in points:
        await session.flush()
        return True, None, False
    point, behind_gateway = await write_point(
        session, room, "setpoint", setpoint, now=now, source="hotel_os"
    )
    return True, point, behind_gateway


async def _track_occupancy(
    session: AsyncSession,
    room: Room,
    occupancy: str,
    reservation_code: str | None,
    now: datetime,
) -> None:
    """Open a period when a guest is in house, close it when the room is no longer occupied."""
    result = await session.execute(
        select(OccupancyPeriod).where(
            OccupancyPeriod.room_id == room.id, OccupancyPeriod.ended_at.is_(None)
        )
    )
    open_period = result.scalars().first()
    if open_period is not None and (
        occupancy != "occupied" or open_period.reservation_code != reservation_code
    ):
        open_period.ended_at = now
        open_period = None
    if occupancy == "occupied" and open_period is None:
        session.add(
            OccupancyPeriod(room_id=room.id, reservation_code=reservation_code, started_at=now)
        )
    await session.flush()


async def meter_history(
    session: AsyncSession, prop: Property, start: datetime, end: datetime
) -> dict:
    """Room code → meter readings ``(measured_at, value)`` in [start, end), plus the last before."""
    room_list = await list_rooms(session, prop)
    codes = {r.id: r.code for r in room_list}
    if not codes:
        return {}
    in_range = await session.execute(
        select(MeterReading.room_id, MeterReading.measured_at, MeterReading.value)
        .where(
            MeterReading.room_id.in_(codes),
            MeterReading.measured_at >= start,
            MeterReading.measured_at < end,
        )
        .order_by(MeterReading.measured_at)
    )
    history: dict = {code: [] for code in codes.values()}
    for room_id in codes:
        before = await session.execute(
            select(MeterReading.measured_at, MeterReading.value)
            .where(MeterReading.room_id == room_id, MeterReading.measured_at < start)
            .order_by(MeterReading.measured_at.desc())
            .limit(1)
        )
        row = before.first()
        if row is not None:
            history[codes[room_id]].append((row.measured_at, row.value))
    for row in in_range:
        history[codes[row.room_id]].append((row.measured_at, row.value))
    return history


async def occupancy_history(
    session: AsyncSession, prop: Property, start: datetime, end: datetime
) -> dict:
    """Room code → occupancy periods ``(started_at, ended_at, reservation)`` overlapping the range."""
    room_list = await list_rooms(session, prop)
    codes = {r.id: r.code for r in room_list}
    if not codes:
        return {}
    result = await session.execute(
        select(OccupancyPeriod)
        .where(
            OccupancyPeriod.room_id.in_(codes),
            OccupancyPeriod.started_at < end,
            (OccupancyPeriod.ended_at.is_(None)) | (OccupancyPeriod.ended_at > start),
        )
        .order_by(OccupancyPeriod.started_at)
    )
    history: dict = {code: [] for code in codes.values()}
    for period in result.scalars():
        history[codes[period.room_id]].append(
            (period.started_at, period.ended_at, period.reservation_code)
        )
    return history
