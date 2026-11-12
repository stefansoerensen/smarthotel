"""The device registry of a property, and the device catalogue."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, get_current_user, get_db, get_scoped_property
from app.core.clock import Clock
from app.core.errors import NotFoundError
from app.models.devices.device import Device
from app.models.devices.gateway import Gateway
from app.models.estate.property import Property
from app.models.platform.user import User
from app.schemas.native.common import Page
from app.schemas.native.devices import (
    CatalogueOut,
    DeviceIn,
    DeviceOut,
    DevicePatch,
    GatewayIn,
    GatewayOut,
    GatewayTokenOut,
    KindOut,
)
from app.services.devices import catalogue, registry

router = APIRouter(tags=["devices"])


def _out(device: Device, gateway_code: str | None) -> DeviceOut:
    return DeviceOut(
        code=device.code,
        name=device.name,
        kind=device.kind,
        protocol=device.protocol,
        address=device.address,
        location=device.location,
        gateway_code=gateway_code,
        controllable=device.controllable,
        safety=catalogue.is_safety(device.kind),
        status=device.status,
        health=device.health,
        last_seen_at=device.last_seen_at,
    )


async def _one(db: AsyncSession, device: Device) -> DeviceOut:
    ids = {device.gateway_id} if device.gateway_id else set()
    codes = await registry.gateway_codes(db, ids)
    return _out(device, codes.get(device.gateway_id) if device.gateway_id else None)


def _gateway_out(gateway: Gateway, clock: Clock) -> GatewayOut:
    return GatewayOut(
        code=gateway.code,
        name=gateway.name,
        status=registry.gateway_status(gateway, clock.now()),
        last_seen_at=gateway.last_seen_at,
        has_token=gateway.token_hash is not None,
    )


@router.get("/device-catalogue", response_model=CatalogueOut)
async def device_catalogue(_: User = Depends(get_current_user)) -> CatalogueOut:
    """Device kinds (with the safety flag) and protocols the registry accepts."""
    return CatalogueOut(
        kinds=[
            KindOut(
                kind=k,
                label=label,
                safety=catalogue.is_safety(k),
                writable=catalogue.can_write(k),
            )
            for k, label in catalogue.DEVICE_KINDS.items()
        ],
        protocols=dict(catalogue.PROTOCOLS),
    )


@router.get("/properties/{property_code}/gateways", response_model=Page[GatewayOut])
async def list_gateways(
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> Page[GatewayOut]:
    """Gateways of a property."""
    rows = await registry.list_gateways(db, prop)
    return Page(items=[_gateway_out(g, clock) for g in rows], total=len(rows))


@router.post(
    "/properties/{property_code}/gateways",
    response_model=GatewayOut,
    status_code=status.HTTP_201_CREATED,
)
async def register_gateway(
    data: GatewayIn,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> GatewayOut:
    """Register an edge gateway."""
    gateway = await registry.register_gateway(db, prop, code=data.code, name=data.name)
    await db.commit()
    return _gateway_out(gateway, clock)


@router.post(
    "/properties/{property_code}/gateways/{gateway_code}/token", response_model=GatewayTokenOut
)
async def create_gateway_token(
    gateway_code: str,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> GatewayTokenOut:
    """Create a new token for the gateway; the old one stops working. Shown once (ADR-0006)."""
    gateway = await registry.find_gateway(db, prop, gateway_code)
    if gateway is None:
        raise NotFoundError("gateway", gateway_code)
    token = await registry.create_gateway_token(db, gateway, now=clock.now())
    await db.commit()
    return GatewayTokenOut(gateway_code=gateway.code, token=token)


@router.get("/properties/{property_code}/devices", response_model=Page[DeviceOut])
async def list_devices(
    kind: str | None = None,
    gateway_code: str | None = None,
    location: str | None = None,
    include_retired: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> Page[DeviceOut]:
    """Devices of a property, filtered by kind, gateway or location."""
    rows, total = await registry.list_devices(
        db,
        prop,
        kind=kind,
        gateway_code=gateway_code,
        location=location,
        include_retired=include_retired,
        skip=skip,
        limit=limit,
    )
    codes = await registry.gateway_codes(db, {d.gateway_id for d in rows if d.gateway_id})
    return Page(
        items=[_out(d, codes.get(d.gateway_id) if d.gateway_id else None) for d in rows],
        total=total,
    )


@router.post(
    "/properties/{property_code}/devices",
    response_model=DeviceOut,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    data: DeviceIn,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> DeviceOut:
    """Register a device. Safety kinds are always read only."""
    device = await registry.register_device(db, prop, **data.model_dump())
    out = await _one(db, device)
    await db.commit()
    return out


@router.get("/properties/{property_code}/devices/{device_code}", response_model=DeviceOut)
async def get_device(
    device_code: str,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> DeviceOut:
    """One device."""
    return await _one(db, await registry.get_device(db, prop, device_code))


@router.patch("/properties/{property_code}/devices/{device_code}", response_model=DeviceOut)
async def patch_device(
    device_code: str,
    data: DevicePatch,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> DeviceOut:
    """Change a device."""
    device = await registry.get_device(db, prop, device_code)
    await registry.update_device(db, prop, device, data.model_dump(exclude_unset=True))
    out = await _one(db, device)
    await db.commit()
    return out


@router.delete("/properties/{property_code}/devices/{device_code}", response_model=DeviceOut)
async def retire_device(
    device_code: str,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> DeviceOut:
    """Retire a device. It stays in the registry with status ``retired``."""
    device = await registry.get_device(db, prop, device_code)
    await registry.retire_device(db, prop, device)
    out = await _one(db, device)
    await db.commit()
    return out
