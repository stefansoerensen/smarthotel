"""Room types, rooms (the digital twin), rollout and the room simulator."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, get_db, get_scoped_property
from app.core.clock import Clock
from app.models.estate.property import Property
from app.models.twin.room import Room
from app.models.twin.room_type import RoomType
from app.schemas.native.common import Page
from app.schemas.native.twin import (
    PointIn,
    PointValueIn,
    RolloutIn,
    RolloutOut,
    RoomOut,
    RoomPointOut,
    RoomTypeIn,
    RoomTypeOut,
    RoomTypePatch,
    SimulatorRoomIn,
    SimulatorStepIn,
    SimulatorStepOut,
    TemplatePointOut,
)
from app.services.devices import registry
from app.services.twin import rooms, templates

router = APIRouter(tags=["twin"])


async def _room_type_out(db: AsyncSession, room_type: RoomType) -> RoomTypeOut:
    points = await templates.list_points(db, room_type)
    return RoomTypeOut(
        code=room_type.code,
        name=room_type.name,
        description=room_type.description,
        points=[
            TemplatePointOut(
                key=p.key,
                label=p.label,
                kind=p.kind,
                protocol=p.protocol,
                unit=p.unit,
                writable=p.writable,
            )
            for p in points
        ],
    )


async def _rooms_out(db: AsyncSession, items: list[Room]) -> list[RoomOut]:
    grouped = await rooms.points_of(db, [r.id for r in items])
    type_codes = await rooms.room_type_codes(db, {r.room_type_id for r in items if r.room_type_id})
    device_ids = {p.device_id for pts in grouped.values() for p in pts if p.device_id}
    dev_codes = await registry.device_codes(db, device_ids)
    return [
        RoomOut(
            code=r.code,
            name=r.name,
            floor=r.floor,
            room_type_code=type_codes.get(r.room_type_id) if r.room_type_id else None,
            points=[
                RoomPointOut(
                    key=p.key,
                    label=p.label,
                    kind=p.kind,
                    unit=p.unit,
                    writable=p.writable,
                    device_code=dev_codes.get(p.device_id) if p.device_id else None,
                    value=p.value,
                    value_at=p.value_at,
                    source=p.source,
                )
                for p in grouped[r.id]
            ],
        )
        for r in items
    ]


# ---------- room types ----------


@router.get("/properties/{property_code}/room-types", response_model=Page[RoomTypeOut])
async def list_room_types(
    prop: Property = Depends(get_scoped_property), db: AsyncSession = Depends(get_db)
) -> Page[RoomTypeOut]:
    """Room types of a property."""
    items = [await _room_type_out(db, rt) for rt in await templates.list_room_types(db, prop)]
    return Page(items=items, total=len(items))


@router.post("/properties/{property_code}/room-types", response_model=RoomTypeOut, status_code=201)
async def create_room_type(
    data: RoomTypeIn,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> RoomTypeOut:
    """Create a room type, optionally with the standard points."""
    room_type = await templates.create_room_type(db, prop, **data.model_dump())
    out = await _room_type_out(db, room_type)
    await db.commit()
    return out


@router.patch("/properties/{property_code}/room-types/{type_code}", response_model=RoomTypeOut)
async def patch_room_type(
    type_code: str,
    data: RoomTypePatch,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> RoomTypeOut:
    """Rename a room type."""
    room_type = await templates.get_room_type(db, prop, type_code)
    await templates.update_room_type(
        db, prop, room_type, name=data.name, description=data.description
    )
    out = await _room_type_out(db, room_type)
    await db.commit()
    return out


@router.post(
    "/properties/{property_code}/room-types/{type_code}/points",
    response_model=RoomTypeOut,
    status_code=201,
)
async def add_point(
    type_code: str,
    data: PointIn,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> RoomTypeOut:
    """Add a data point to a room type."""
    room_type = await templates.get_room_type(db, prop, type_code)
    await templates.add_point(db, prop, room_type, templates.PointSpec(**data.model_dump()))
    out = await _room_type_out(db, room_type)
    await db.commit()
    return out


@router.delete(
    "/properties/{property_code}/room-types/{type_code}/points/{key}", response_model=RoomTypeOut
)
async def remove_point(
    type_code: str,
    key: str,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> RoomTypeOut:
    """Remove a data point from a room type; rooms already rolled out keep theirs."""
    room_type = await templates.get_room_type(db, prop, type_code)
    await templates.remove_point(db, prop, room_type, key)
    out = await _room_type_out(db, room_type)
    await db.commit()
    return out


# ---------- rooms ----------


@router.post("/properties/{property_code}/rollout", response_model=RolloutOut)
async def rollout(
    data: RolloutIn,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> RolloutOut:
    """Roll a room type out to rooms: rooms, devices and twin points in one step."""
    room_type = await templates.get_room_type(db, prop, data.room_type_code)
    result = await rooms.rollout(db, prop, room_type, data.room_codes, floor=data.floor)
    await db.commit()
    return RolloutOut(
        rooms_created=result.rooms_created,
        rooms_unchanged=result.rooms_unchanged,
        devices_created=result.devices_created,
        conflicts=result.conflicts,
    )


@router.get("/properties/{property_code}/rooms", response_model=Page[RoomOut])
async def list_rooms(
    prop: Property = Depends(get_scoped_property), db: AsyncSession = Depends(get_db)
) -> Page[RoomOut]:
    """All rooms of a property with their twin points."""
    items = await _rooms_out(db, await rooms.list_rooms(db, prop))
    return Page(items=items, total=len(items))


@router.get("/properties/{property_code}/rooms/{room_code}", response_model=RoomOut)
async def get_room(
    room_code: str,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> RoomOut:
    """One room with its twin points."""
    return (await _rooms_out(db, [await rooms.get_room(db, prop, room_code)]))[0]


@router.put("/properties/{property_code}/rooms/{room_code}/points/{key}", response_model=RoomOut)
async def write_point(
    room_code: str,
    key: str,
    data: PointValueIn,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> RoomOut:
    """Set a writable point (set point, light, …) in the twin."""
    room = await rooms.get_room(db, prop, room_code)
    await rooms.write_point(db, room, key, data.value, now=clock.now(), source="manual")
    out = (await _rooms_out(db, [room]))[0]
    await db.commit()
    return out


# ---------- simulator ----------


@router.post("/properties/{property_code}/simulator/step", response_model=SimulatorStepOut)
async def simulator_step(
    data: SimulatorStepIn,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> SimulatorStepOut:
    """Advance the simulation of every room of the property."""
    count = await rooms.simulate_step(
        db, prop, minutes=data.minutes, outdoor=data.outdoor, now=clock.now()
    )
    await db.commit()
    return SimulatorStepOut(rooms=count, minutes=data.minutes, outdoor=data.outdoor)


@router.post("/properties/{property_code}/simulator/rooms/{room_code}", response_model=RoomOut)
async def simulator_room(
    room_code: str,
    data: SimulatorRoomIn,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> RoomOut:
    """Open or close the window or mark presence of a simulated room."""
    room = await rooms.get_room(db, prop, room_code)
    await rooms.simulate_inputs(
        db, room, window=data.window, presence=data.presence, now=clock.now()
    )
    out = (await _rooms_out(db, [room]))[0]
    await db.commit()
    return out
