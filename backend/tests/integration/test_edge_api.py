"""The edge API: gateway tokens, readings, heartbeat and commands (ADR-0006)."""

import hashlib
import json
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.devices.gateway import Gateway
from tests.factories import create_property

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "edge-v1"


def _contract(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text())


async def _edge_property(
    client: AsyncClient, db: AsyncSession, headers: dict[str, str]
) -> tuple[str, str]:
    """A property DEMO-like setup: room type, rooms 101-102 behind gateway GW-01; returns (code, token)."""
    code = str((await create_property(db)).code)
    base = f"/api/properties/{code}"
    await client.post(
        f"{base}/gateways", json={"code": "GW-01", "name": "Technik"}, headers=headers
    )
    await client.post(
        f"{base}/room-types",
        json={"code": "STD", "name": "Standard", "standard_points": True},
        headers=headers,
    )
    await client.post(
        f"{base}/rollout",
        json={"room_type_code": "STD", "room_codes": ["101", "102"], "gateway_code": "GW-01"},
        headers=headers,
    )
    token = (await client.post(f"{base}/gateways/GW-01/token", headers=headers)).json()["token"]
    return code, token


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_token_is_shown_once_and_stored_as_hash(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code, token = await _edge_property(client, db, admin_headers)
    assert len(token) >= 40
    gateway = (await db.execute(select(Gateway).where(Gateway.code == "GW-01"))).scalars().first()
    assert gateway.token_hash == hashlib.sha256(token.encode()).hexdigest()
    listed = await client.get(f"/api/properties/{code}/gateways", headers=admin_headers)
    assert token not in json.dumps(listed.json())
    assert listed.json()["items"][0]["has_token"] is True

    new = (
        await client.post(f"/api/properties/{code}/gateways/GW-01/token", headers=admin_headers)
    ).json()
    assert (await client.post("/edge/v1/hello", headers=_bearer(token))).status_code == 401
    assert (await client.post("/edge/v1/hello", headers=_bearer(new["token"]))).status_code == 200


async def test_hello_lists_devices_of_the_gateway(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code, token = await _edge_property(client, db, admin_headers)
    response = await client.post("/edge/v1/hello", headers=_bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == set(_contract("hello-response.json"))
    assert body["property_code"] == code
    setpoint = next(d for d in body["devices"] if d["code"] == "101-SETPOINT")
    assert set(setpoint) == set(_contract("hello-response.json")["devices"][0])
    assert setpoint["controllable"] is True
    assert setpoint["room_code"] == "101"
    assert setpoint["point_key"] == "setpoint"
    assert len(body["devices"]) == 14


async def test_without_or_with_wrong_token_is_401(client: AsyncClient) -> None:
    assert (await client.post("/edge/v1/hello")).status_code == 401
    assert (await client.post("/edge/v1/hello", headers=_bearer("x" * 43))).status_code == 401


async def test_readings_update_the_twin_and_ignore_older_values(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code, token = await _edge_property(client, db, admin_headers)
    sample = _contract("readings-request.json")
    response = await client.post("/edge/v1/readings", json=sample, headers=_bearer(token))
    assert response.status_code == 200
    assert response.json() == {"accepted": 2, "ignored": 0}

    room = (await client.get(f"/api/properties/{code}/rooms/101", headers=admin_headers)).json()
    temperature = next(p for p in room["points"] if p["key"] == "temperature")
    assert temperature["value"] == 20.4
    assert temperature["source"] == "edge"
    assert temperature["value_at"].startswith("2026-11-12T08:05:00")

    older = {
        "readings": [
            {
                "device_code": "101-TEMPERATURE",
                "value": 15.0,
                "measured_at": "2026-11-12T08:00:00+00:00",
            },
            {"device_code": "UNKNOWN", "value": 1.0, "measured_at": "2026-11-12T08:10:00+00:00"},
        ]
    }
    again = await client.post("/edge/v1/readings", json=older, headers=_bearer(token))
    assert again.json() == {"accepted": 0, "ignored": 2}


async def test_heartbeat_sets_gateway_online_and_device_health(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code, token = await _edge_property(client, db, admin_headers)
    beat = _contract("heartbeat-request.json")
    beat["health"][0]["ok"] = False
    response = await client.post("/edge/v1/heartbeat", json=beat, headers=_bearer(token))
    assert response.status_code == 200
    gateways = (await client.get(f"/api/properties/{code}/gateways", headers=admin_headers)).json()
    assert gateways["items"][0]["status"] == "online"
    assert gateways["items"][0]["last_seen_at"] is not None
    device = (
        await client.get(f"/api/properties/{code}/devices/101-TEMPERATURE", headers=admin_headers)
    ).json()
    assert device["health"] == "fault"
    ok = (
        await client.get(f"/api/properties/{code}/devices/101-SETPOINT", headers=admin_headers)
    ).json()
    assert ok["health"] == "ok"


async def test_set_point_of_an_edge_room_becomes_a_command(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code, token = await _edge_property(client, db, admin_headers)
    written = await client.put(
        f"/api/properties/{code}/rooms/101/points/setpoint",
        json={"value": 21.5},
        headers=admin_headers,
    )
    assert written.status_code == 200
    setpoint = next(p for p in written.json()["points"] if p["key"] == "setpoint")
    assert setpoint["desired"] == 21.5
    assert setpoint["value"] is None
    assert written.json()["gateway_code"] == "GW-01"

    commands = await client.get("/edge/v1/commands", headers=_bearer(token))
    body = commands.json()
    assert set(body) == set(_contract("commands-response.json"))
    assert len(body["commands"]) == 1
    command = body["commands"][0]
    assert set(command) == set(_contract("commands-response.json")["commands"][0])
    assert command["device_code"] == "101-SETPOINT"
    assert command["value"] == 21.5
    assert (await client.get("/edge/v1/commands", headers=_bearer(token))).json()["commands"] == []

    ack = await client.post(
        f"/edge/v1/commands/{command['id']}/ack",
        json=_contract("ack-request.json"),
        headers=_bearer(token),
    )
    assert ack.status_code == 200
    assert ack.json()["status"] == "done"
    listed = await client.get(f"/api/properties/{code}/commands", headers=admin_headers)
    assert listed.json()["items"][0]["status"] == "done"

    reading = {
        "readings": [
            {
                "device_code": "101-SETPOINT",
                "value": 21.5,
                "measured_at": "2026-11-12T08:07:00+00:00",
            }
        ]
    }
    await client.post("/edge/v1/readings", json=reading, headers=_bearer(token))
    room = (await client.get(f"/api/properties/{code}/rooms/101", headers=admin_headers)).json()
    setpoint = next(p for p in room["points"] if p["key"] == "setpoint")
    assert setpoint["value"] == 21.5
    assert setpoint["desired"] is None


async def test_ack_of_another_gateways_command_is_404(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code, token = await _edge_property(client, db, admin_headers)
    other_code, other_token = await _edge_property(client, db, admin_headers)
    await client.put(
        f"/api/properties/{code}/rooms/101/points/setpoint",
        json={"value": 22},
        headers=admin_headers,
    )
    command = (await client.get("/edge/v1/commands", headers=_bearer(token))).json()["commands"][0]
    foreign = await client.post(
        f"/edge/v1/commands/{command['id']}/ack",
        json={"status": "done"},
        headers=_bearer(other_token),
    )
    assert foreign.status_code == 404


async def test_cloud_simulator_skips_edge_rooms(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code, _ = await _edge_property(client, db, admin_headers)
    await client.post(
        f"/api/properties/{code}/rollout",
        json={"room_type_code": "STD", "room_codes": ["201"]},
        headers=admin_headers,
    )
    step = await client.post(
        f"/api/properties/{code}/simulator/step", json={"minutes": 30}, headers=admin_headers
    )
    assert step.json()["rooms"] == 1
    room = (await client.get(f"/api/properties/{code}/rooms/101", headers=admin_headers)).json()
    assert next(p for p in room["points"] if p["key"] == "temperature")["value"] is None
    toggle = await client.post(
        f"/api/properties/{code}/simulator/rooms/101", json={"window": True}, headers=admin_headers
    )
    assert toggle.status_code == 422
    assert toggle.json()["code"] == "twin.edge_room"
