"""Coupling with the Hotel OS: link, sync, webhook, faults (ADR-0007)."""

import hmac
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, get_db, get_scoped_property
from app.core.clock import Clock
from app.core.config import settings
from app.core.errors import DomainError, NotFoundError
from app.models.estate.property import Property
from app.models.integration.hotel_os_link import HotelOsLink
from app.services.energy import aggregate
from app.services.integration import faults as faults_service
from app.services.integration import occupancy
from app.services.integration import overview as overview_service
from app.services.integration.hotel_os import HotelOs, configured_client

router = APIRouter(tags=["hotel-os"])


def get_hotel_os_client() -> HotelOs:
    """The configured Hotel OS client; tests override this dependency."""
    client = configured_client()
    if client is None:
        raise DomainError(
            "hotel_os.not_configured",
            "HOTEL_OS_URL, HOTEL_OS_USERNAME and HOTEL_OS_PASSWORD are not set",
        )
    return client


class LinkIn(BaseModel):
    """Link a property to its Hotel OS property."""

    hotel_os_property_code: str = Field(min_length=1, max_length=20)
    enabled: bool = True
    comfort_setpoint: float = Field(default=21.0, ge=15, le=26)
    eco_setpoint: float = Field(default=17.0, ge=7, le=24)
    energy_price_eur_per_kwh: Decimal | None = Field(default=None, ge=0, le=10, decimal_places=4)


class LinkOut(BaseModel):
    """The link and the last sync."""

    hotel_os_property_code: str | None
    enabled: bool
    comfort_setpoint: float
    eco_setpoint: float
    energy_price_eur_per_kwh: str | None
    last_sync_at: datetime | None
    last_sync_error: str | None
    configured: bool


class SyncOut(BaseModel):
    """What a sync changed."""

    rooms_changed: int
    unmatched_units: list[str]


class FaultOut(BaseModel):
    """One building fault for the inbox."""

    kind: str
    severity: str
    message: str
    unit_name: str | None
    since: datetime | None


class FaultsOut(BaseModel):
    """Faults of one property."""

    property_code: str
    items: list[FaultOut]


def _configured() -> bool:
    return bool(settings.hotel_os_url and settings.hotel_os_username and settings.hotel_os_password)


def _link_out(link: HotelOsLink | None) -> LinkOut:
    if link is None:
        return LinkOut(
            hotel_os_property_code=None,
            enabled=False,
            comfort_setpoint=21.0,
            eco_setpoint=17.0,
            energy_price_eur_per_kwh=None,
            last_sync_at=None,
            last_sync_error=None,
            configured=_configured(),
        )
    return LinkOut(
        hotel_os_property_code=link.hotel_os_property_code,
        enabled=link.enabled,
        comfort_setpoint=link.comfort_setpoint,
        eco_setpoint=link.eco_setpoint,
        energy_price_eur_per_kwh=(
            str(link.energy_price_eur_per_kwh)
            if link.energy_price_eur_per_kwh is not None
            else None
        ),
        last_sync_at=link.last_sync_at,
        last_sync_error=link.last_sync_error,
        configured=_configured(),
    )


def _today(prop: Property, now: datetime):
    return now.astimezone(ZoneInfo(prop.time_zone)).date()


@router.get("/properties/{property_code}/hotel-os", response_model=LinkOut)
async def get_link(
    prop: Property = Depends(get_scoped_property), db: AsyncSession = Depends(get_db)
) -> LinkOut:
    """The property's link to the Hotel OS."""
    return _link_out(await occupancy.find_link(db, prop))


@router.put("/properties/{property_code}/hotel-os", response_model=LinkOut)
async def put_link(
    data: LinkIn,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> LinkOut:
    """Create or change the link."""
    link = await occupancy.save_link(db, prop, **data.model_dump())
    out = _link_out(link)
    await db.commit()
    return out


@router.post("/properties/{property_code}/hotel-os/sync", response_model=SyncOut)
async def sync(
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
    hotel_os: HotelOs = Depends(get_hotel_os_client),
) -> SyncOut:
    """Read occupancy from the Hotel OS now and set room modes."""
    link = await occupancy.find_link(db, prop)
    if link is None or not link.enabled:
        raise DomainError("hotel_os.not_linked", "This property is not linked to the Hotel OS")
    now = clock.now()
    try:
        result = await occupancy.sync_property(
            db, prop, link, hotel_os, today=_today(prop, now), now=now
        )
    except Exception:
        await db.commit()  # keep last_sync_error
        raise
    await db.commit()
    return SyncOut(rooms_changed=result.rooms_changed, unmatched_units=result.unmatched_units)


@router.get("/properties/{property_code}/faults", response_model=FaultsOut)
async def property_faults(
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> FaultsOut:
    """Building faults of the property, as the Hotel OS inbox sees them."""
    items = await faults_service.faults(db, prop, now=clock.now())
    return FaultsOut(property_code=prop.code, items=[FaultOut(**f.__dict__) for f in items])


def _matches(given: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


class WebhookOut(BaseModel):
    """Properties synced because of the webhook."""

    synced: list[str]


@router.post("/integrations/hotel-os/webhook", response_model=WebhookOut)
async def webhook(
    payload: dict,
    request: Request,
    token: str = Query(""),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> WebhookOut:
    """A Hotel OS webhook: a Reservation event triggers a sync of the linked properties.

    The token is checked before anything else, so the answer to a stranger is always 401.
    """
    if not _matches(token, settings.hotel_os_webhook_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("topic") != "Reservation" or not payload.get("propertyId"):
        return WebhookOut(synced=[])
    provider = request.app.dependency_overrides.get(get_hotel_os_client, get_hotel_os_client)
    hotel_os: HotelOs = provider()
    synced: list[str] = []
    now = clock.now()
    for link in await occupancy.links_for(db, str(payload["propertyId"])):
        prop = await db.get(Property, link.property_id)
        if prop is None:
            continue
        await occupancy.sync_property(db, prop, link, hotel_os, today=_today(prop, now), now=now)
        synced.append(prop.code)
    await db.commit()
    return WebhookOut(synced=synced)


@router.get("/integrations/hotel-os/v1/faults", response_model=FaultsOut)
async def inbox_faults(
    property_code: str,
    x_api_key: str = Header(""),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> FaultsOut:
    """Faults for the Hotel OS inbox, by Hotel OS property code, with the inbox key."""
    if not _matches(x_api_key, settings.hotel_os_inbox_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid key")
    result = await db.execute(
        select(HotelOsLink).where(HotelOsLink.hotel_os_property_code == property_code)
    )
    items: list[FaultOut] = []
    links = list(result.scalars())
    if not links:
        raise NotFoundError("hotel_os_link", property_code)
    now = clock.now()
    for link in links:
        prop = await db.get(Property, link.property_id)
        if prop is not None:
            items.extend(
                FaultOut(**f.__dict__) for f in await faults_service.faults(db, prop, now=now)
            )
    return FaultsOut(property_code=property_code, items=items)


class UnitEnergy(BaseModel):
    """One unit's night."""

    unit_name: str
    kwh: float
    occupied: bool
    reservation_code: str | None
    cost_eur: str | None


class EnergyOut(BaseModel):
    """Energy of one night for the Hotel OS live P&L (hub d31)."""

    property_code: str
    date: date
    kwh_total: float
    occupied_nights: int
    kwh_per_occupied_night: float | None
    price_eur_per_kwh: str | None
    cost_eur: str | None
    by_unit: list[UnitEnergy]


@router.get("/integrations/hotel-os/v1/energy", response_model=EnergyOut)
async def energy_for_pl(
    property_code: str,
    date_: date = Query(alias="date"),
    x_api_key: str = Header(""),
    db: AsyncSession = Depends(get_db),
) -> EnergyOut:
    """kWh and cost of one night (12:00–12:00 local) per unit, for the Hotel OS live P&L."""
    if not _matches(x_api_key, settings.hotel_os_inbox_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid key")
    result = await db.execute(
        select(HotelOsLink).where(HotelOsLink.hotel_os_property_code == property_code)
    )
    link = result.scalars().first()
    if link is None:
        raise NotFoundError("hotel_os_link", property_code)
    prop = await db.get(Property, link.property_id)
    items = await aggregate.nights(db, prop, first=date_, last=date_)
    price = link.energy_price_eur_per_kwh
    occupied = [n for n in items if n.occupied]
    total = round(sum(n.kwh for n in items), 3)
    per_night = round(sum(n.kwh for n in occupied) / len(occupied), 3) if occupied else None
    return EnergyOut(
        property_code=property_code,
        date=date_,
        kwh_total=total,
        occupied_nights=len(occupied),
        kwh_per_occupied_night=per_night,
        price_eur_per_kwh=str(price) if price is not None else None,
        cost_eur=aggregate.money(total, price),
        by_unit=[
            UnitEnergy(
                unit_name=n.room_code,
                kwh=n.kwh,
                occupied=n.occupied,
                reservation_code=n.reservation_code,
                cost_eur=aggregate.money(n.kwh, price),
            )
            for n in items
        ],
    )


class OverviewOut(BaseModel):
    """One-look figures of a property."""

    rooms: dict[str, int]
    modes: dict[str, int]
    avg_temperature_occupied: float | None
    faults: dict[str, int]
    gateways: dict[str, int]
    kwh_yesterday: float
    pending_commands: int


@router.get("/properties/{property_code}/overview", response_model=OverviewOut)
async def property_overview(
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> OverviewOut:
    """Rooms by occupancy and mode, comfort, faults, gateways, energy yesterday, open commands."""
    return OverviewOut(**await overview_service.overview(db, prop, now=clock.now()))
