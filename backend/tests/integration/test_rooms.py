"""Rooms, the digital twin and rollout of a room type."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_property, events_of


async def _setup(client: AsyncClient, db: AsyncSession, headers: dict[str, str]) -> str:
    code = str((await create_property(db)).code)
    await client.post(
        f"/api/properties/{code}/room-types",
        json={"code": "STD", "name": "Standardzimmer", "standard_points": True},
        headers=headers,
    )
    return code


async def test_rollout_creates_rooms_devices_and_twin(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(client, db, admin_headers)
    rooms = ["101", "102", "103", "104", "105"]
    response = await client.post(
        f"/api/properties/{code}/rollout",
        json={"room_type_code": "STD", "room_codes": rooms, "floor": "1"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "rooms_created": 5,
        "rooms_unchanged": 0,
        "devices_created": 35,
        "conflicts": [],
    }

    listed = await client.get(f"/api/properties/{code}/rooms", headers=admin_headers)
    assert [r["code"] for r in listed.json()["items"]] == rooms
    room = (await client.get(f"/api/properties/{code}/rooms/103", headers=admin_headers)).json()
    assert room["room_type_code"] == "STD"
    assert room["floor"] == "1"
    temperature = next(p for p in room["points"] if p["key"] == "temperature")
    assert temperature["device_code"] == "103-TEMPERATURE"
    assert temperature["value"] is None

    device = await client.get(f"/api/properties/{code}/devices/103-SETPOINT", headers=admin_headers)
    assert device.json()["name"] == "Sollwert 103"
    assert device.json()["location"] == "103"
    assert await events_of(db, "room", f"{code}/103") == ["created"]


async def test_rollout_is_idempotent_and_reports_conflicts(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(client, db, admin_headers)
    await client.post(
        f"/api/properties/{code}/room-types",
        json={"code": "SUITE", "name": "Suite", "standard_points": True},
        headers=admin_headers,
    )
    url = f"/api/properties/{code}/rollout"
    await client.post(
        url, json={"room_type_code": "STD", "room_codes": ["201", "202"]}, headers=admin_headers
    )
    again = await client.post(
        url,
        json={"room_type_code": "STD", "room_codes": ["201", "202", "203"]},
        headers=admin_headers,
    )
    assert again.json() == {
        "rooms_created": 1,
        "rooms_unchanged": 2,
        "devices_created": 7,
        "conflicts": [],
    }
    other = await client.post(
        url, json={"room_type_code": "SUITE", "room_codes": ["203", "204"]}, headers=admin_headers
    )
    assert other.json()["conflicts"] == ["203"]
    assert other.json()["rooms_created"] == 1


async def test_rollout_limit(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(client, db, admin_headers)
    response = await client.post(
        f"/api/properties/{code}/rollout",
        json={"room_type_code": "STD", "room_codes": [str(n) for n in range(1000, 1501)]},
        headers=admin_headers,
    )
    assert response.status_code == 422


async def test_write_point_values(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(client, db, admin_headers)
    await client.post(
        f"/api/properties/{code}/rollout",
        json={"room_type_code": "STD", "room_codes": ["301"]},
        headers=admin_headers,
    )
    base = f"/api/properties/{code}/rooms/301/points"
    ok = await client.put(f"{base}/setpoint", json={"value": 21.5}, headers=admin_headers)
    assert ok.status_code == 200, ok.text
    setpoint = next(p for p in ok.json()["points"] if p["key"] == "setpoint")
    assert setpoint["value"] == 21.5
    assert setpoint["source"] == "manual"
    assert setpoint["value_at"] is not None

    sensor = await client.put(f"{base}/temperature", json={"value": 30}, headers=admin_headers)
    assert sensor.status_code == 422
    assert sensor.json()["code"] == "twin.point_read_only"
    missing = await client.put(f"{base}/nope", json={"value": 1}, headers=admin_headers)
    assert missing.status_code == 404
