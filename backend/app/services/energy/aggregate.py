"""Energy from cumulative meter readings: per 15 minutes, per day, per occupied night (SB4).

A delta between two consecutive readings belongs to the interval of the later reading. A falling
counter (meter replaced or reset) counts nothing. Nights run from 12:00 to 12:00 local time; a
night is occupied when a stay covers its midnight. Feeds the live P&L (hub d31).
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.services.twin import rooms

if TYPE_CHECKING:
    from app.models.estate.property import Property

QUARTER = timedelta(minutes=15)
MAX_QUARTER_DAYS = 7
MAX_DAYS = 366
CENT = Decimal("0.01")


@dataclass(frozen=True)
class Reading:
    """A cumulative counter value at a time."""

    at: datetime
    value: float


def quarter_edges(start: datetime, end: datetime) -> list[datetime]:
    """Edges every 15 minutes from ``start`` to ``end``."""
    edges = [start]
    while edges[-1] < end:
        edges.append(edges[-1] + QUARTER)
    return edges


def day_edges(first: date, last: date, time_zone: str) -> list[datetime]:
    """Local midnights from ``first`` to the day after ``last``, as aware datetimes in UTC."""
    zone = ZoneInfo(time_zone)
    days = (last - first).days + 2
    return [
        datetime.combine(first + timedelta(days=i), time(0), zone).astimezone(ZoneInfo("UTC"))
        for i in range(days)
    ]


def night_edges(night: date, time_zone: str) -> tuple[datetime, datetime, datetime]:
    """(start 12:00, midnight, end 12:00 next day) of the night of ``night``, in UTC."""
    zone = ZoneInfo(time_zone)
    utc = ZoneInfo("UTC")
    start = datetime.combine(night, time(12), zone).astimezone(utc)
    midnight = datetime.combine(night + timedelta(days=1), time(0), zone).astimezone(utc)
    end = datetime.combine(night + timedelta(days=1), time(12), zone).astimezone(utc)
    return start, midnight, end


def consumption_by_bucket(readings: list[Reading], edges: list[datetime]) -> list[float]:
    """kWh per interval between consecutive ``edges``."""
    totals = [0.0] * (len(edges) - 1)
    ordered = sorted(readings, key=lambda r: r.at)
    for previous, current in zip(ordered, ordered[1:], strict=False):
        delta = current.value - previous.value
        if delta <= 0 or current.at < edges[0] or current.at >= edges[-1]:
            continue
        totals[bisect_right(edges, current.at) - 1] += delta
    return [round(t, 3) for t in totals]


def check_range(first: date, last: date, *, max_days: int) -> None:
    """Refuse reversed or too long ranges."""
    if last < first:
        raise DomainError("energy.range_reversed", "'to' lies before 'from'")
    if (last - first).days + 1 > max_days:
        raise DomainError("energy.range_too_long", f"At most {max_days} days at this resolution")


@dataclass(frozen=True)
class Series:
    """Consumption of a property over a range."""

    starts: list[datetime]
    kwh: list[float]
    by_room: dict[str, float]


async def series(
    session: AsyncSession,
    prop: Property,
    *,
    first: date,
    last: date,
    resolution: str,
    room_code: str | None = None,
) -> Series:
    """kWh per 15 minutes or per local day, and per room, from ``first`` to ``last`` inclusive."""
    if resolution == "15min":
        check_range(first, last, max_days=MAX_QUARTER_DAYS)
        days = day_edges(first, last, prop.time_zone)
        edges = quarter_edges(days[0], days[-1])
    elif resolution == "day":
        check_range(first, last, max_days=MAX_DAYS)
        edges = day_edges(first, last, prop.time_zone)
    else:
        raise DomainError("energy.resolution", "Resolution is '15min' or 'day'")
    history = await rooms.meter_history(session, prop, edges[0], edges[-1])
    totals = [0.0] * (len(edges) - 1)
    by_room: dict[str, float] = {}
    for code, rows in history.items():
        if room_code is not None and code != room_code:
            continue
        buckets = consumption_by_bucket([Reading(at, value) for at, value in rows], edges)
        by_room[code] = round(sum(buckets), 3)
        totals = [a + b for a, b in zip(totals, buckets, strict=True)]
    return Series(starts=edges[:-1], kwh=[round(t, 3) for t in totals], by_room=by_room)


@dataclass(frozen=True)
class Night:
    """One room in one night."""

    night: date
    room_code: str
    occupied: bool
    reservation_code: str | None
    kwh: float


async def nights(session: AsyncSession, prop: Property, *, first: date, last: date) -> list[Night]:
    """kWh per room and night, and whether a guest slept there."""
    check_range(first, last, max_days=MAX_DAYS)
    range_start = night_edges(first, prop.time_zone)[0]
    range_end = night_edges(last, prop.time_zone)[2]
    meters = await rooms.meter_history(session, prop, range_start, range_end)
    stays = await rooms.occupancy_history(session, prop, range_start, range_end)
    result: list[Night] = []
    day = first
    while day <= last:
        start, midnight, end = night_edges(day, prop.time_zone)
        for code in sorted(meters):
            kwh = consumption_by_bucket(
                [Reading(at, value) for at, value in meters[code]], [start, end]
            )[0]
            stay = next(
                (
                    s
                    for s in stays.get(code, [])
                    if s[0] <= midnight and (s[1] is None or s[1] > midnight)
                ),
                None,
            )
            result.append(Night(day, code, stay is not None, stay[2] if stay else None, kwh))
        day += timedelta(days=1)
    return result


def money(kwh: float, price: Decimal | None) -> str | None:
    """Cost of ``kwh`` at ``price`` per kWh, rounded to cents, as a string; None without price."""
    if price is None:
        return None
    return str((Decimal(str(kwh)) * price).quantize(CENT, rounding=ROUND_HALF_EVEN))
