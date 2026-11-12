"""Simulator endpoints drive the twin."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_property


def _value(room: dict, key: str) -> float | None:
    return next(p["value"] for p in room["points"] if p["key"] == key)


async def test_simulation_heats_and_window_cools(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = str((await create_property(db)).code)
    await client.post(
        f"/api/properties/{code}/room-types",
        json={"code": "STD", "name": "Standard", "standard_points": True},
        headers=admin_headers,
    )
    await client.post(
        f"/api/properties/{code}/rollout",
        json={"room_type_code": "STD", "room_codes": ["101", "102"]},
        headers=admin_headers,
    )
    first = await client.post(
        f"/api/properties/{code}/simulator/step", json={"minutes": 60}, headers=admin_headers
    )
    assert first.status_code == 200, first.text
    assert first.json()["rooms"] == 2
    room = (await client.get(f"/api/properties/{code}/rooms/101", headers=admin_headers)).json()
    # Fresh rooms start at 18 °C with a set point of 21 °C.
    assert 18.0 < _value(room, "temperature") < 21.0
    assert _value(room, "valve") > 0
    temp_point = next(p for p in room["points"] if p["key"] == "temperature")
    assert temp_point["source"] == "simulator"

    opened = await client.post(
        f"/api/properties/{code}/simulator/rooms/102", json={"window": True}, headers=admin_headers
    )
    assert opened.status_code == 200
    assert _value(opened.json(), "window") == 1
    await client.post(
        f"/api/properties/{code}/simulator/step", json={"minutes": 60}, headers=admin_headers
    )
    r101 = (await client.get(f"/api/properties/{code}/rooms/101", headers=admin_headers)).json()
    r102 = (await client.get(f"/api/properties/{code}/rooms/102", headers=admin_headers)).json()
    assert _value(r102, "valve") == 0
    assert _value(r102, "temperature") < _value(r101, "temperature")


async def test_step_limits(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = str((await create_property(db)).code)
    response = await client.post(
        f"/api/properties/{code}/simulator/step", json={"minutes": 0}, headers=admin_headers
    )
    assert response.status_code == 422
    empty = await client.post(
        f"/api/properties/{code}/simulator/step", json={"minutes": 15}, headers=admin_headers
    )
    assert empty.json()["rooms"] == 0
