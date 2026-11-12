"""Building faults for the Hotel OS exception inbox (ADR-0007)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.devices import registry
from app.services.twin import rooms

if TYPE_CHECKING:
    from app.models.estate.property import Property

COLD_MARGIN = 2.0
SEVERITY_ORDER = {"Blocker": 0, "Today": 1, "Attention": 2}


@dataclass(frozen=True)
class Fault:
    """One thing the front desk should know about the building."""

    kind: str
    severity: str
    message: str
    unit_name: str | None
    since: datetime | None


def _num(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


async def faults(session: AsyncSession, prop: Property, *, now: datetime) -> list[Fault]:
    """Cold occupied or arriving rooms, offline gateways and faulty devices, most urgent first."""
    items: list[Fault] = []
    local = ZoneInfo(prop.time_zone)

    room_list = await rooms.list_rooms(session, prop)
    grouped = await rooms.points_of(session, [r.id for r in room_list])
    for room in room_list:
        if room.occupancy not in ("occupied", "arriving"):
            continue
        points = {p.key: p for p in grouped[room.id]}
        temperature = points.get("temperature")
        setpoint = points.get("setpoint")
        if temperature is None or setpoint is None or temperature.value is None:
            continue
        target = setpoint.value if setpoint.value is not None else setpoint.desired
        if target is not None and temperature.value < target - COLD_MARGIN:
            items.append(
                Fault(
                    "RoomTooCold",
                    "Today",
                    f"Zimmer {room.code} zu kalt: {_num(temperature.value)} °C, Soll {_num(target)} °C",
                    room.code,
                    temperature.value_at,
                )
            )

    for gateway in await registry.list_gateways(session, prop):
        if registry.gateway_status(gateway, now) == "offline" and gateway.last_seen_at:
            since = gateway.last_seen_at.astimezone(local).strftime("%H:%M")
            items.append(
                Fault(
                    "GatewayOffline",
                    "Today",
                    f"Gateway {gateway.code} seit {since} nicht erreichbar",
                    None,
                    gateway.last_seen_at,
                )
            )

    devices, _ = await registry.list_devices(session, prop, limit=10_000)
    for device in devices:
        if device.health == "fault":
            items.append(
                Fault(
                    "DeviceFault",
                    "Attention",
                    f"Gerät {device.code} meldet eine Störung",
                    device.location,
                    device.last_seen_at,
                )
            )
    return sorted(items, key=lambda f: (SEVERITY_ORDER[f.severity], f.unit_name or ""))
