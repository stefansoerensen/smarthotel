"""Energy per interval and per occupied night (SB4, input for the live P&L, hub d31)."""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_scoped_property
from app.models.estate.property import Property
from app.services.energy import aggregate
from app.services.integration import occupancy

router = APIRouter(tags=["energy"])


class Bucket(BaseModel):
    """kWh in one interval."""

    start: datetime
    kwh: float


class RoomTotal(BaseModel):
    """kWh of one room over the range."""

    room_code: str
    kwh: float


class SeriesOut(BaseModel):
    """Consumption over a range."""

    resolution: str
    buckets: list[Bucket]
    rooms: list[RoomTotal]
    total_kwh: float


class NightOut(BaseModel):
    """One room in one night."""

    date: date
    room_code: str
    occupied: bool
    reservation_code: str | None
    kwh: float


class NightsSummary(BaseModel):
    """Totals over the nights."""

    occupied_nights: int
    kwh_occupied: float
    kwh_vacant: float
    kwh_per_occupied_night: float | None
    price_eur_per_kwh: str | None
    cost_per_occupied_night_eur: str | None


class NightsOut(BaseModel):
    """Nights with their consumption."""

    nights: list[NightOut]
    summary: NightsSummary


@router.get("/properties/{property_code}/energy", response_model=SeriesOut)
async def energy(
    from_: date = Query(alias="from"),
    to: date = Query(),
    resolution: str = Query("day"),
    room: str | None = None,
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> SeriesOut:
    """kWh per 15 minutes (up to 7 days) or per local day, and per room."""
    result = await aggregate.series(
        db, prop, first=from_, last=to, resolution=resolution, room_code=room
    )
    return SeriesOut(
        resolution=resolution,
        buckets=[Bucket(start=s, kwh=k) for s, k in zip(result.starts, result.kwh, strict=True)],
        rooms=[RoomTotal(room_code=c, kwh=k) for c, k in sorted(result.by_room.items())],
        total_kwh=round(sum(result.kwh), 3),
    )


def summarise(items: list[aggregate.Night], price: Decimal | None) -> NightsSummary:
    """Totals and the kWh and cost per occupied night."""
    occupied = [n for n in items if n.occupied]
    kwh_occupied = round(sum(n.kwh for n in occupied), 3)
    per_night = round(kwh_occupied / len(occupied), 3) if occupied else None
    return NightsSummary(
        occupied_nights=len(occupied),
        kwh_occupied=kwh_occupied,
        kwh_vacant=round(sum(n.kwh for n in items if not n.occupied), 3),
        kwh_per_occupied_night=per_night,
        price_eur_per_kwh=str(price) if price is not None else None,
        cost_per_occupied_night_eur=(
            aggregate.money(per_night, price) if per_night is not None else None
        ),
    )


@router.get("/properties/{property_code}/energy/nights", response_model=NightsOut)
async def energy_nights(
    from_: date = Query(alias="from"),
    to: date = Query(),
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> NightsOut:
    """kWh per room and night (12:00–12:00 local) and per occupied night."""
    items = await aggregate.nights(db, prop, first=from_, last=to)
    link = await occupancy.find_link(db, prop)
    price = link.energy_price_eur_per_kwh if link else None
    return NightsOut(
        nights=[
            NightOut(
                date=n.night,
                room_code=n.room_code,
                occupied=n.occupied,
                reservation_code=n.reservation_code,
                kwh=n.kwh,
            )
            for n in items
        ],
        summary=summarise(items, price),
    )
