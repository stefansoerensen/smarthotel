"""One-look overview of a property: rooms, comfort, faults, gateways, energy, commands."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.devices import registry
from app.services.edge import commands
from app.services.energy import aggregate
from app.services.integration import faults as faults_service
from app.services.twin import rooms

if TYPE_CHECKING:
    from app.models.estate.property import Property


async def overview(session: AsyncSession, prop: Property, *, now: datetime) -> dict[str, Any]:
    """Counts and figures for the property header and the property list."""
    room_list = await rooms.list_rooms(session, prop)
    occupancy = {"occupied": 0, "arriving": 0, "vacant": 0, "unknown": 0}
    modes = {"comfort": 0, "preheat": 0, "eco": 0}
    for room in room_list:
        occupancy[room.occupancy if room.occupancy in occupancy else "unknown"] += 1
        if room.mode in modes:
            modes[room.mode] += 1

    grouped = await rooms.points_of(session, [r.id for r in room_list])
    temps = [
        p.value
        for r in room_list
        if r.occupancy == "occupied"
        for p in grouped[r.id]
        if p.key == "temperature" and p.value is not None
    ]

    items = await faults_service.faults(session, prop, now=now)
    gateways = await registry.list_gateways(session, prop)
    statuses = [registry.gateway_status(g, now) for g in gateways]

    yesterday = now.astimezone(ZoneInfo(prop.time_zone)).date() - timedelta(days=1)
    series = await aggregate.series(
        session, prop, first=yesterday, last=yesterday, resolution="day"
    )

    return {
        "rooms": {"total": len(room_list), **occupancy},
        "modes": modes,
        "avg_temperature_occupied": round(sum(temps) / len(temps), 1) if temps else None,
        "faults": {
            "total": len(items),
            "blocker": sum(f.severity == "Blocker" for f in items),
            "today": sum(f.severity == "Today" for f in items),
            "attention": sum(f.severity == "Attention" for f in items),
        },
        "gateways": {
            "total": len(gateways),
            "online": statuses.count("online"),
            "offline": statuses.count("offline"),
            "never": statuses.count("provisioned"),
        },
        "kwh_yesterday": round(sum(series.kwh), 3),
        "pending_commands": await commands.count_open(session, prop),
    }
