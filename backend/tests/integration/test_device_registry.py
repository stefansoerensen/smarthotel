"""The device registry: gateways and devices per property."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import auth_headers, create_property, create_tenant, events_of


async def _setup(db: AsyncSession) -> str:
    prop = await create_property(db)
    return str(prop.code)


async def test_register_gateway_and_devices(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(db)
    gw = await client.post(
        f"/api/properties/{code}/gateways",
        json={"code": "GW-01", "name": "Technikraum UG"},
        headers=admin_headers,
    )
    assert gw.status_code == 201, gw.text
    assert gw.json()["status"] == "provisioned"

    dev = await client.post(
        f"/api/properties/{code}/devices",
        json={
            "code": "R101-VALVE",
            "name": "Heizventil Zimmer 101",
            "kind": "valve",
            "protocol": "knx",
            "address": "1/2/3",
            "location": "101",
            "gateway_code": "GW-01",
            "controllable": True,
        },
        headers=admin_headers,
    )
    assert dev.status_code == 201, dev.text
    body = dev.json()
    assert body["controllable"] is True
    assert body["gateway_code"] == "GW-01"
    assert body["safety"] is False
    assert await events_of(db, "device", f"{code}/R101-VALVE") == ["registered"]
    assert await events_of(db, "gateway", f"{code}/GW-01") == ["registered"]


async def test_device_codes_are_unique_per_property(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(db)
    payload = {"code": "D1", "name": "x", "kind": "light", "protocol": "knx"}
    first = await client.post(
        f"/api/properties/{code}/devices", json=payload, headers=admin_headers
    )
    assert first.status_code == 201
    again = await client.post(
        f"/api/properties/{code}/devices", json=payload, headers=admin_headers
    )
    assert again.status_code == 409
    assert again.json()["code"] == "device.code_taken"

    other = await _setup(db)
    elsewhere = await client.post(
        f"/api/properties/{other}/devices", json=payload, headers=admin_headers
    )
    assert elsewhere.status_code == 201


async def test_safety_devices_are_always_read_only(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(db)
    created = await client.post(
        f"/api/properties/{code}/devices",
        json={
            "code": "SD-101",
            "name": "Rauchmelder 101",
            "kind": "smoke_detector",
            "protocol": "bacnet",
            "controllable": True,
        },
        headers=admin_headers,
    )
    assert created.status_code == 422
    assert created.json()["code"] == "device.safety_read_only"

    created = await client.post(
        f"/api/properties/{code}/devices",
        json={
            "code": "SD-101",
            "name": "Rauchmelder 101",
            "kind": "smoke_detector",
            "protocol": "bacnet",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201
    assert created.json()["controllable"] is False
    assert created.json()["safety"] is True

    patched = await client.patch(
        f"/api/properties/{code}/devices/SD-101", json={"controllable": True}, headers=admin_headers
    )
    assert patched.status_code == 422
    assert patched.json()["code"] == "device.safety_read_only"


async def test_changing_kind_to_safety_drops_control(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(db)
    await client.post(
        f"/api/properties/{code}/devices",
        json={
            "code": "X1",
            "name": "x",
            "kind": "other",
            "protocol": "modbus",
            "controllable": True,
        },
        headers=admin_headers,
    )
    patched = await client.patch(
        f"/api/properties/{code}/devices/X1", json={"kind": "fire_alarm"}, headers=admin_headers
    )
    assert patched.status_code == 200
    assert patched.json()["controllable"] is False


async def test_unknown_kind_protocol_or_gateway_is_rejected(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(db)
    url = f"/api/properties/{code}/devices"
    bad_kind = await client.post(
        url,
        json={"code": "A", "name": "x", "kind": "toaster", "protocol": "knx"},
        headers=admin_headers,
    )
    assert bad_kind.json()["code"] == "device.unknown_kind"
    bad_proto = await client.post(
        url,
        json={"code": "A", "name": "x", "kind": "light", "protocol": "zigbee"},
        headers=admin_headers,
    )
    assert bad_proto.json()["code"] == "device.unknown_protocol"
    bad_gw = await client.post(
        url,
        json={"code": "A", "name": "x", "kind": "light", "protocol": "knx", "gateway_code": "NONE"},
        headers=admin_headers,
    )
    assert bad_gw.status_code == 404


async def test_filter_devices_and_retire(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(db)
    url = f"/api/properties/{code}/devices"
    for dev_code, kind, location in [
        ("101-T", "temperature_sensor", "101"),
        ("101-W", "window_contact", "101"),
        ("102-T", "temperature_sensor", "102"),
    ]:
        await client.post(
            url,
            json={
                "code": dev_code,
                "name": dev_code,
                "kind": kind,
                "protocol": "knx",
                "location": location,
            },
            headers=admin_headers,
        )
    by_kind = await client.get(url, params={"kind": "temperature_sensor"}, headers=admin_headers)
    assert {d["code"] for d in by_kind.json()["items"]} == {"101-T", "102-T"}
    by_room = await client.get(url, params={"location": "101"}, headers=admin_headers)
    assert by_room.json()["total"] == 2

    retired = await client.delete(f"{url}/101-W", headers=admin_headers)
    assert retired.status_code == 200
    assert retired.json()["status"] == "retired"
    active = await client.get(url, params={"location": "101"}, headers=admin_headers)
    assert {d["code"] for d in active.json()["items"]} == {"101-T"}
    assert await events_of(db, "device", f"{code}/101-W") == ["registered", "retired"]


async def test_operator_reads_but_cannot_change_registry_of_other_tenant(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    own = await create_tenant(db)
    mine = await create_property(db, tenant=own)
    theirs = await create_property(db)
    headers = await auth_headers(db, role="operator", tenant=own)

    ok = await client.post(
        f"/api/properties/{mine.code}/devices",
        json={"code": "L1", "name": "Licht", "kind": "light", "protocol": "knx"},
        headers=headers,
    )
    assert ok.status_code == 201
    hidden = await client.get(f"/api/properties/{theirs.code}/devices", headers=headers)
    assert hidden.status_code == 404


async def test_catalogue_endpoint(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    response = await client.get("/api/device-catalogue", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "knx" in body["protocols"]
    smoke = next(k for k in body["kinds"] if k["kind"] == "smoke_detector")
    assert smoke["safety"] is True
    assert smoke["writable"] is False
    valve = next(k for k in body["kinds"] if k["kind"] == "valve")
    assert valve["writable"] is True
