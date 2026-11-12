"""Room types: templates of data points per property."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import auth_headers, create_property, create_tenant, events_of


async def _prop(db: AsyncSession) -> str:
    return str((await create_property(db)).code)


async def test_create_room_type_with_standard_points(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _prop(db)
    response = await client.post(
        f"/api/properties/{code}/room-types",
        json={"code": "STD", "name": "Standardzimmer", "standard_points": True},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    keys = [p["key"] for p in body["points"]]
    assert keys == ["temperature", "setpoint", "window", "presence", "valve", "light", "heat_meter"]
    writable = {p["key"] for p in body["points"] if p["writable"]}
    assert writable == {"setpoint", "valve", "light"}
    assert await events_of(db, "room_type", f"{code}/STD") == ["created"]


async def test_add_and_remove_points(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _prop(db)
    base = f"/api/properties/{code}/room-types"
    await client.post(base, json={"code": "S", "name": "Suite"}, headers=admin_headers)
    added = await client.post(
        f"{base}/S/points",
        json={
            "key": "fan",
            "label": "Fan-Coil",
            "kind": "fan_coil",
            "protocol": "knx",
            "writable": True,
        },
        headers=admin_headers,
    )
    assert added.status_code == 201, added.text
    assert [p["key"] for p in added.json()["points"]] == ["fan"]

    duplicate = await client.post(
        f"{base}/S/points",
        json={"key": "fan", "label": "x", "kind": "fan_coil", "protocol": "knx"},
        headers=admin_headers,
    )
    assert duplicate.status_code == 409

    removed = await client.delete(f"{base}/S/points/fan", headers=admin_headers)
    assert removed.status_code == 200
    assert removed.json()["points"] == []


async def test_sensor_and_safety_points_cannot_be_writable(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _prop(db)
    base = f"/api/properties/{code}/room-types"
    await client.post(base, json={"code": "S", "name": "Suite"}, headers=admin_headers)
    for kind in ("temperature_sensor", "smoke_detector"):
        response = await client.post(
            f"{base}/S/points",
            json={"key": kind, "label": kind, "kind": kind, "protocol": "knx", "writable": True},
            headers=admin_headers,
        )
        assert response.status_code == 422
        assert response.json()["code"] == "twin.point_read_only"
    ok = await client.post(
        f"{base}/S/points",
        json={
            "key": "smoke",
            "label": "Rauchmelder",
            "kind": "smoke_detector",
            "protocol": "bacnet",
        },
        headers=admin_headers,
    )
    assert ok.status_code == 201
    assert ok.json()["points"][0]["writable"] is False


async def test_room_type_codes_unique_per_property_and_scoped(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    own = await create_tenant(db)
    mine = await create_property(db, tenant=own)
    other = await create_property(db)
    payload = {"code": "STD", "name": "Standard"}
    assert (
        await client.post(
            f"/api/properties/{mine.code}/room-types", json=payload, headers=admin_headers
        )
    ).status_code == 201
    again = await client.post(
        f"/api/properties/{mine.code}/room-types", json=payload, headers=admin_headers
    )
    assert again.status_code == 409
    assert (
        await client.post(
            f"/api/properties/{other.code}/room-types", json=payload, headers=admin_headers
        )
    ).status_code == 201

    operator = await auth_headers(db, role="operator", tenant=own)
    listed = await client.get(f"/api/properties/{mine.code}/room-types", headers=operator)
    assert [rt["code"] for rt in listed.json()["items"]] == ["STD"]
    hidden = await client.get(f"/api/properties/{other.code}/room-types", headers=operator)
    assert hidden.status_code == 404
