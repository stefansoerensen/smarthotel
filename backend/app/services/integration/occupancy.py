"""Occupancy from the Hotel OS sets room modes (ADR-0007)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, DomainError
from app.models.integration.hotel_os_link import HotelOsLink
from app.services.devices import registry
from app.services.edge import commands
from app.services.integration.hotel_os import HotelOs, Stay
from app.services.twin import rooms

if TYPE_CHECKING:
    from app.models.estate.property import Property

MODE_OF = {"occupied": "comfort", "arriving": "preheat", "vacant": "eco"}


@dataclass
class SyncResult:
    """What a sync changed."""

    rooms_changed: int = 0
    unmatched_units: list[str] = field(default_factory=list)


async def find_link(session: AsyncSession, prop: Property) -> HotelOsLink | None:
    """The property's link, or None."""
    result = await session.execute(select(HotelOsLink).where(HotelOsLink.property_id == prop.id))
    return result.scalar_one_or_none()


async def links_for(session: AsyncSession, hotel_os_property_code: str) -> list[HotelOsLink]:
    """Enabled links to one Hotel OS property."""
    result = await session.execute(
        select(HotelOsLink).where(
            HotelOsLink.hotel_os_property_code == hotel_os_property_code,
            HotelOsLink.enabled.is_(True),
        )
    )
    return list(result.scalars())


async def save_link(
    session: AsyncSession,
    prop: Property,
    *,
    hotel_os_property_code: str,
    enabled: bool,
    comfort_setpoint: float,
    eco_setpoint: float,
) -> HotelOsLink:
    """Create or change the property's link."""
    if eco_setpoint > comfort_setpoint:
        raise DomainError("hotel_os.setpoints", "The eco set point must not exceed comfort")
    link = await find_link(session, prop)
    if link is None:
        link = HotelOsLink(property_id=prop.id)
        session.add(link)
    link.hotel_os_property_code = hotel_os_property_code.strip()
    link.enabled = enabled
    link.comfort_setpoint = comfort_setpoint
    link.eco_setpoint = eco_setpoint
    await session.flush()
    return link


def occupancy_by_unit(stays: list[Stay], today: date) -> dict[str, tuple[str, str]]:
    """Unit name → (occupancy, reservation code). In house wins over an arrival."""
    result: dict[str, tuple[str, str]] = {}
    for stay in stays:
        if not stay.unit_name:
            continue
        if stay.status == "InHouse":
            result[stay.unit_name] = ("occupied", stay.reservation_code)
        elif stay.status == "Confirmed" and stay.arrival_date == today:
            result.setdefault(stay.unit_name, ("arriving", stay.reservation_code))
    return result


async def sync_property(
    session: AsyncSession,
    prop: Property,
    link: HotelOsLink,
    hotel_os: HotelOs,
    *,
    today: date,
    now: datetime,
) -> SyncResult:
    """Read the current stays and set every room's occupancy and mode."""
    try:
        stays = await hotel_os.current_stays(link.hotel_os_property_code, today)
    except AppError as exc:
        link.last_sync_at = now
        link.last_sync_error = exc.message[:500]
        await session.flush()
        raise
    by_unit = occupancy_by_unit(stays, today)
    result = SyncResult()
    known = set()
    for room in await rooms.list_rooms(session, prop):
        known.add(room.code)
        occupancy, reservation = by_unit.get(room.code, ("vacant", None))
        mode = MODE_OF[occupancy]
        setpoint = link.eco_setpoint if mode == "eco" else link.comfort_setpoint
        changed, point, behind_gateway = await rooms.apply_mode(
            session,
            prop,
            room,
            occupancy=occupancy,
            mode=mode,
            reservation_code=reservation,
            setpoint=setpoint,
            now=now,
        )
        if changed:
            result.rooms_changed += 1
        if point is not None and behind_gateway and point.device_id is not None:
            device = await registry.get_device_by_id(session, point.device_id)
            if device.controllable:
                await commands.create(
                    session, prop, device, key="setpoint", value=setpoint, now=now
                )
    result.unmatched_units = sorted(unit for unit in by_unit if unit not in known)
    link.last_sync_at = now
    link.last_sync_error = None
    await session.flush()
    return result
