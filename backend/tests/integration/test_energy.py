"""Energy per interval and per occupied night (SB4, input for the live P&L, d31)."""

import json
from datetime import date
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.native.hotel_os import get_hotel_os_client
from app.services.integration.hotel_os import Stay
from tests.factories import create_property

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "hotel-os-v1"


class FakeHotelOs:
    def __init__(self, stays: list[Stay]) -> None:
        self.stays = stays

    async def current_stays(self, property_code: str, today: date) -> list[Stay]:
        return list(self.stays)


async def _setup(
    client: AsyncClient, db: AsyncSession, headers: dict[str, str]
) -> tuple[str, dict[str, str]]:
    code = str((await create_property(db)).code)
    base = f"/api/properties/{code}"
    await client.post(
        f"{base}/room-types",
        json={"code": "STD", "name": "Std", "standard_points": True},
        headers=headers,
    )
    await client.post(f"{base}/gateways", json={"code": "GW", "name": "GW"}, headers=headers)
    await client.post(
        f"{base}/rollout",
        json={"room_type_code": "STD", "room_codes": ["101", "102"], "gateway_code": "GW"},
        headers=headers,
    )
    await client.put(
        f"{base}/hotel-os",
        json={"hotel_os_property_code": "HAM", "enabled": True, "energy_price_eur_per_kwh": "0.12"},
        headers=headers,
    )
    stay = Stay("R1", "101", "InHouse", date(2026, 11, 11), date(2026, 11, 14))
    client._transport.app.dependency_overrides[get_hotel_os_client] = lambda: FakeHotelOs([stay])  # type: ignore[attr-defined]
    await client.post(f"{base}/hotel-os/sync", headers=headers)  # at 2026-11-12T08:00Z
    token = (await client.post(f"{base}/gateways/GW/token", headers=headers)).json()["token"]
    edge = {"Authorization": f"Bearer {token}"}
    readings = [
        ("101-HEAT-METER", 10.0, "2026-11-12T08:00:00+00:00"),
        ("102-HEAT-METER", 5.0, "2026-11-12T08:00:00+00:00"),
        ("101-HEAT-METER", 12.0, "2026-11-12T20:00:00+00:00"),
        ("101-HEAT-METER", 15.0, "2026-11-13T06:00:00+00:00"),
        ("102-HEAT-METER", 5.4, "2026-11-13T06:00:00+00:00"),
        ("101-HEAT-METER", 15.5, "2026-11-13T11:00:00+00:00"),
    ]
    for device, value, measured in readings:
        response = await client.post(
            "/edge/v1/readings",
            json={"readings": [{"device_code": device, "value": value, "measured_at": measured}]},
            headers=edge,
        )
        assert response.json()["accepted"] == 1
    return code, headers


async def test_daily_and_quarter_hour_consumption(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code, headers = await _setup(client, db, admin_headers)
    daily = await client.get(
        f"/api/properties/{code}/energy",
        params={"resolution": "day", "from": "2026-11-12", "to": "2026-11-13"},
        headers=headers,
    )
    assert daily.status_code == 200, daily.text
    body = daily.json()
    assert [b["kwh"] for b in body["buckets"]] == [2.0, 3.9]
    assert body["total_kwh"] == 5.9
    assert {r["room_code"]: r["kwh"] for r in body["rooms"]} == {"101": 5.5, "102": 0.4}

    quarters = await client.get(
        f"/api/properties/{code}/energy",
        params={"resolution": "15min", "from": "2026-11-12", "to": "2026-11-12", "room": "101"},
        headers=headers,
    )
    buckets = quarters.json()["buckets"]
    assert len(buckets) == 96
    assert [b for b in buckets if b["kwh"]] == [{"start": "2026-11-12T20:00:00Z", "kwh": 2.0}]


async def test_energy_per_occupied_night(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code, headers = await _setup(client, db, admin_headers)
    response = await client.get(
        f"/api/properties/{code}/energy/nights",
        params={"from": "2026-11-12", "to": "2026-11-12"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    nights = {n["room_code"]: n for n in response.json()["nights"]}
    assert nights["101"] == {
        "date": "2026-11-12",
        "room_code": "101",
        "occupied": True,
        "reservation_code": "R1",
        "kwh": 5.0,
    }
    assert nights["102"]["occupied"] is False
    assert nights["102"]["kwh"] == 0.4
    summary = response.json()["summary"]
    assert summary == {
        "occupied_nights": 1,
        "kwh_occupied": 5.0,
        "kwh_vacant": 0.4,
        "kwh_per_occupied_night": 5.0,
        "price_eur_per_kwh": "0.1200",
        "cost_per_occupied_night_eur": "0.60",
    }


async def test_energy_for_the_live_pl(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str], monkeypatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "hotel_os_inbox_key", "inbox-key-0123456789")
    code, _ = await _setup(client, db, admin_headers)
    url = "/api/integrations/hotel-os/v1/energy?property_code=HAM&date=2026-11-12"
    assert (await client.get(url)).status_code == 401
    response = await client.get(url, headers={"X-Api-Key": "inbox-key-0123456789"})
    assert response.status_code == 200
    body = response.json()
    contract = json.loads((CONTRACTS / "energy-response.json").read_text())
    assert set(body) == set(contract)
    assert set(body["by_unit"][0]) == set(contract["by_unit"][0])
    assert body["date"] == "2026-11-12"
    assert body["kwh_total"] == 5.4
    assert body["occupied_nights"] == 1
    assert body["kwh_per_occupied_night"] == 5.0
    assert body["cost_eur"] == "0.65"
    unit = next(u for u in body["by_unit"] if u["unit_name"] == "101")
    assert unit == {
        "unit_name": "101",
        "kwh": 5.0,
        "occupied": True,
        "reservation_code": "R1",
        "cost_eur": "0.60",
    }


async def test_range_limits(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = str((await create_property(db)).code)
    too_long = await client.get(
        f"/api/properties/{code}/energy",
        params={"resolution": "15min", "from": "2026-11-01", "to": "2026-11-12"},
        headers=admin_headers,
    )
    assert too_long.status_code == 422
    reversed_range = await client.get(
        f"/api/properties/{code}/energy/nights",
        params={"from": "2026-11-12", "to": "2026-11-01"},
        headers=admin_headers,
    )
    assert reversed_range.status_code == 422
