"""Edge protocol v1: the API gateways call with their token (ADR-0006)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, get_db
from app.core.clock import Clock
from app.models.devices.gateway import Gateway
from app.models.estate.property import Property
from app.models.twin.room import RoomPoint
from app.schemas.edge import (
    AckIn,
    AckOut,
    CommandsOut,
    EdgeCommand,
    EdgeDevice,
    HeartbeatIn,
    HeartbeatOut,
    HelloOut,
    ReadingsIn,
    ReadingsOut,
)
from app.services.devices import registry
from app.services.edge import commands
from app.services.twin import rooms

router = APIRouter(prefix="/edge/v1", tags=["edge"])
_bearer = HTTPBearer(auto_error=False)


async def get_gateway(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Gateway:
    """The gateway identified by the bearer token, else 401."""
    gateway = None
    if credentials is not None:
        gateway = await registry.gateway_for_token(db, credentials.credentials)
    if gateway is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown gateway")
    return gateway


@router.post("/hello", response_model=HelloOut)
async def hello(
    gateway: Gateway = Depends(get_gateway), db: AsyncSession = Depends(get_db)
) -> HelloOut:
    """The gateway's devices, with the room and point each one feeds."""
    prop = await db.get(Property, gateway.property_id)
    devices = await registry.gateway_devices(db, gateway)
    points = (
        await db.execute(
            select(RoomPoint.device_id, RoomPoint.key, RoomPoint.room_id).where(
                RoomPoint.device_id.in_([d.id for d in devices])
            )
        )
    ).all()
    by_device = {row.device_id: row for row in points}
    room_codes = await _room_codes(db, {row.room_id for row in points})
    return HelloOut(
        gateway_code=gateway.code,
        property_code=prop.code if prop else "",
        devices=[
            EdgeDevice(
                code=d.code,
                kind=d.kind,
                protocol=d.protocol,
                address=d.address,
                controllable=d.controllable,
                room_code=room_codes.get(by_device[d.id].room_id) if d.id in by_device else None,
                point_key=by_device[d.id].key if d.id in by_device else None,
            )
            for d in devices
        ],
    )


async def _room_codes(db: AsyncSession, room_ids: set) -> dict:
    from app.models.twin.room import Room

    if not room_ids:
        return {}
    rows = await db.execute(select(Room.id, Room.code).where(Room.id.in_(room_ids)))
    return {row.id: row.code for row in rows}


@router.post("/readings", response_model=ReadingsOut)
async def readings(
    data: ReadingsIn,
    gateway: Gateway = Depends(get_gateway),
    db: AsyncSession = Depends(get_db),
) -> ReadingsOut:
    """Apply readings to the twin; older or unknown ones are ignored, so replays are harmless."""
    devices = {d.code: d for d in await registry.gateway_devices(db, gateway)}
    accepted = ignored = 0
    for reading in sorted(data.readings, key=lambda r: r.measured_at):
        device = devices.get(reading.device_code)
        if device is not None and await rooms.apply_reading(
            db, device.id, reading.value, reading.measured_at
        ):
            accepted += 1
        else:
            ignored += 1
    await db.commit()
    return ReadingsOut(accepted=accepted, ignored=ignored)


@router.post("/heartbeat", response_model=HeartbeatOut)
async def heartbeat(
    data: HeartbeatIn,
    gateway: Gateway = Depends(get_gateway),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> HeartbeatOut:
    """Mark the gateway online and store device health."""
    await registry.record_heartbeat(
        db, gateway, {h.device_code: h.ok for h in data.health}, now=clock.now()
    )
    await db.commit()
    return HeartbeatOut(status="online")


@router.get("/commands", response_model=CommandsOut)
async def take_commands(
    gateway: Gateway = Depends(get_gateway),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> CommandsOut:
    """Pending commands for this gateway; each is handed out once."""
    taken = await commands.take_pending(db, gateway, now=clock.now())
    out = CommandsOut(
        commands=[
            EdgeCommand(id=c.id, device_code=c.device_code, value=c.value, created_at=c.created_at)
            for c in taken
        ]
    )
    await db.commit()
    return out


@router.post("/commands/{command_id}/ack", response_model=AckOut)
async def ack(
    command_id: uuid.UUID,
    data: AckIn,
    gateway: Gateway = Depends(get_gateway),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> AckOut:
    """Store the gateway's answer: done, failed or refused."""
    command = await commands.acknowledge(
        db, gateway, command_id, status=data.status, detail=data.detail, now=clock.now()
    )
    await db.commit()
    return AckOut(id=command.id, status=command.status)
