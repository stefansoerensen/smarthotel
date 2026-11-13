"""Overview of a property: rooms, comfort, faults, gateways, energy."""

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.native.hotel_os import get_hotel_os_client
from app.services.integration.hotel_os import Stay
from tests.factories import create_property


class FakeHotelOs:
    async def current_stays(self, property_code: str, today: date) -> list[Stay]:
        return [Stay("R1", "101", "InHouse", date(2026, 11, 11), date(2026, 11, 14))]


async def test_overview(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = str((await create_property(db)).code)
    base = f"/api/properties/{code}"
    empty = await client.get(f"{base}/overview", headers=admin_headers)
    assert empty.status_code == 200, empty.text
    assert empty.json()["rooms"] == {
        "total": 0,
        "occupied": 0,
        "arriving": 0,
        "vacant": 0,
        "unknown": 0,
    }

    await client.post(
        f"{base}/room-types",
        json={"code": "STD", "name": "S", "standard_points": True},
        headers=admin_headers,
    )
    await client.post(f"{base}/gateways", json={"code": "GW", "name": "GW"}, headers=admin_headers)
    await client.post(
        f"{base}/rollout",
        json={"room_type_code": "STD", "room_codes": ["101", "102", "103"], "gateway_code": "GW"},
        headers=admin_headers,
    )
    await client.put(
        f"{base}/hotel-os", json={"hotel_os_property_code": "HAM"}, headers=admin_headers
    )
    client._transport.app.dependency_overrides[get_hotel_os_client] = lambda: FakeHotelOs()  # type: ignore[attr-defined]
    await client.post(f"{base}/hotel-os/sync", headers=admin_headers)
    token = (await client.post(f"{base}/gateways/GW/token", headers=admin_headers)).json()["token"]
    edge = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/edge/v1/readings",
        json={
            "readings": [
                {
                    "device_code": "101-TEMPERATURE",
                    "value": 17.5,
                    "measured_at": "2026-11-12T07:59:00+00:00",
                }
            ]
        },
        headers=edge,
    )
    await client.post(
        "/edge/v1/heartbeat",
        json={"sent_at": "2026-11-12T07:59:00+00:00", "health": []},
        headers=edge,
    )

    body = (await client.get(f"{base}/overview", headers=admin_headers)).json()
    assert body["rooms"] == {"total": 3, "occupied": 1, "arriving": 0, "vacant": 2, "unknown": 0}
    assert body["modes"] == {"comfort": 1, "preheat": 0, "eco": 2}
    assert body["avg_temperature_occupied"] == 17.5
    assert body["faults"] == {"total": 1, "today": 1, "attention": 0, "blocker": 0}
    assert body["gateways"] == {"total": 1, "online": 1, "offline": 0, "never": 0}
    assert body["kwh_yesterday"] == 0.0
    assert body["pending_commands"] == 3
