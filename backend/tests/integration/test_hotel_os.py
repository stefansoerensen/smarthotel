"""Coupling with the Hotel OS: occupancy sync, webhook, faults (ADR-0007)."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock
from app.api.native.hotel_os import get_hotel_os_client
from app.services.integration.hotel_os import Stay
from tests.factories import NOW, create_property, events_of

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "hotel-os-v1"
TODAY = date(2026, 11, 12)


class FakeHotelOs:
    """Answers like the Hotel OS for one property."""

    def __init__(self) -> None:
        self.stays: list[Stay] = []
        self.calls: list[tuple[str, date]] = []

    async def current_stays(self, property_code: str, today: date) -> list[Stay]:
        self.calls.append((property_code, today))
        return list(self.stays)


@pytest.fixture
def hotel_os(client: AsyncClient) -> FakeHotelOs:
    fake = FakeHotelOs()
    client._transport.app.dependency_overrides[get_hotel_os_client] = lambda: fake  # type: ignore[attr-defined]
    return fake


def _stay(code: str, unit: str | None, status: str, arrival: date = TODAY) -> Stay:
    return Stay(code, unit, status, arrival, arrival + timedelta(days=2))


async def _setup(
    client: AsyncClient, db: AsyncSession, headers: dict[str, str], gateway: bool = False
) -> str:
    code = str((await create_property(db)).code)
    base = f"/api/properties/{code}"
    await client.post(
        f"{base}/room-types",
        json={"code": "STD", "name": "Std", "standard_points": True},
        headers=headers,
    )
    rollout = {"room_type_code": "STD", "room_codes": ["101", "102", "103", "104"]}
    if gateway:
        await client.post(f"{base}/gateways", json={"code": "GW", "name": "GW"}, headers=headers)
        rollout["gateway_code"] = "GW"
    await client.post(f"{base}/rollout", json=rollout, headers=headers)
    linked = await client.put(
        f"{base}/hotel-os", json={"hotel_os_property_code": "HAM", "enabled": True}, headers=headers
    )
    assert linked.status_code == 200, linked.text
    return code


def _point(room: dict, key: str) -> dict:
    return next(p for p in room["points"] if p["key"] == key)


async def test_sync_sets_modes_and_set_points(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str], hotel_os: FakeHotelOs
) -> None:
    code = await _setup(client, db, admin_headers)
    hotel_os.stays = [
        _stay("R1", "101", "InHouse", TODAY - timedelta(days=1)),
        _stay("R2", "102", "Confirmed"),
        _stay("R3", "999", "InHouse"),
        _stay("R4", None, "Confirmed"),
    ]
    response = await client.post(f"/api/properties/{code}/hotel-os/sync", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["rooms_changed"] == 4
    assert response.json()["unmatched_units"] == ["999"]
    assert hotel_os.calls == [("HAM", TODAY)]

    rooms = {
        r["code"]: r
        for r in (await client.get(f"/api/properties/{code}/rooms", headers=admin_headers)).json()[
            "items"
        ]
    }
    assert (rooms["101"]["occupancy"], rooms["101"]["mode"]) == ("occupied", "comfort")
    assert rooms["101"]["reservation_code"] == "R1"
    assert (rooms["102"]["occupancy"], rooms["102"]["mode"]) == ("arriving", "preheat")
    assert (rooms["103"]["occupancy"], rooms["103"]["mode"]) == ("vacant", "eco")
    assert _point(rooms["101"], "setpoint")["value"] == 21.0
    assert _point(rooms["102"], "setpoint")["value"] == 21.0
    assert _point(rooms["103"], "setpoint")["value"] == 17.0
    assert _point(rooms["103"], "setpoint")["source"] == "hotel_os"
    assert await events_of(db, "room", f"{code}/101") == ["created", "mode_changed"]

    again = await client.post(f"/api/properties/{code}/hotel-os/sync", headers=admin_headers)
    assert again.json()["rooms_changed"] == 0
    link = (await client.get(f"/api/properties/{code}/hotel-os", headers=admin_headers)).json()
    assert link["last_sync_at"] is not None
    assert link["last_sync_error"] is None


async def test_guest_adjustment_is_kept_until_the_mode_changes(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str], hotel_os: FakeHotelOs
) -> None:
    code = await _setup(client, db, admin_headers)
    hotel_os.stays = [_stay("R1", "101", "InHouse")]
    await client.post(f"/api/properties/{code}/hotel-os/sync", headers=admin_headers)
    await client.put(
        f"/api/properties/{code}/rooms/101/points/setpoint",
        json={"value": 23},
        headers=admin_headers,
    )
    await client.post(f"/api/properties/{code}/hotel-os/sync", headers=admin_headers)
    room = (await client.get(f"/api/properties/{code}/rooms/101", headers=admin_headers)).json()
    assert _point(room, "setpoint")["value"] == 23
    hotel_os.stays = []
    await client.post(f"/api/properties/{code}/hotel-os/sync", headers=admin_headers)
    room = (await client.get(f"/api/properties/{code}/rooms/101", headers=admin_headers)).json()
    assert room["mode"] == "eco"
    assert _point(room, "setpoint")["value"] == 17.0


async def test_rooms_behind_a_gateway_get_commands(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str], hotel_os: FakeHotelOs
) -> None:
    code = await _setup(client, db, admin_headers, gateway=True)
    hotel_os.stays = [_stay("R1", "101", "InHouse")]
    await client.post(f"/api/properties/{code}/hotel-os/sync", headers=admin_headers)
    commands = (await client.get(f"/api/properties/{code}/commands", headers=admin_headers)).json()
    by_device = {c["device_code"]: c["value"] for c in commands["items"]}
    assert by_device["101-SETPOINT"] == 21.0
    assert by_device["102-SETPOINT"] == 17.0
    room = (await client.get(f"/api/properties/{code}/rooms/101", headers=admin_headers)).json()
    assert _point(room, "setpoint")["desired"] == 21.0


async def test_sync_without_link_or_disabled(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str], hotel_os: FakeHotelOs
) -> None:
    code = str((await create_property(db)).code)
    response = await client.post(f"/api/properties/{code}/hotel-os/sync", headers=admin_headers)
    assert response.status_code == 422
    assert response.json()["code"] == "hotel_os.not_linked"


async def test_webhook_triggers_a_sync(
    client: AsyncClient,
    db: AsyncSession,
    admin_headers: dict[str, str],
    hotel_os: FakeHotelOs,
    monkeypatch,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "hotel_os_webhook_token", "hook-secret-0123456789")
    code = await _setup(client, db, admin_headers)
    hotel_os.stays = [_stay("R1", "101", "InHouse")]
    payload = json.loads((CONTRACTS / "webhook-request.json").read_text())

    wrong = await client.post("/api/integrations/hotel-os/webhook?token=nope", json=payload)
    assert wrong.status_code == 401
    ok = await client.post(
        "/api/integrations/hotel-os/webhook?token=hook-secret-0123456789", json=payload
    )
    assert ok.status_code == 200
    assert ok.json() == {"synced": [code]}
    room = (await client.get(f"/api/properties/{code}/rooms/101", headers=admin_headers)).json()
    assert room["mode"] == "comfort"

    other_topic = await client.post(
        "/api/integrations/hotel-os/webhook?token=hook-secret-0123456789",
        json={**payload, "topic": "Folio"},
    )
    assert other_topic.json() == {"synced": []}
    unknown = await client.post(
        "/api/integrations/hotel-os/webhook?token=hook-secret-0123456789",
        json={**payload, "propertyId": "XYZ"},
    )
    assert unknown.json() == {"synced": []}


async def test_webhook_is_closed_without_a_configured_token(client: AsyncClient) -> None:
    response = await client.post("/api/integrations/hotel-os/webhook?token=", json={})
    assert response.status_code == 401


async def test_faults_for_the_inbox(
    client: AsyncClient,
    db: AsyncSession,
    admin_headers: dict[str, str],
    hotel_os: FakeHotelOs,
    monkeypatch,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "hotel_os_inbox_key", "inbox-key-0123456789")
    code = await _setup(client, db, admin_headers, gateway=True)
    base = f"/api/properties/{code}"
    hotel_os.stays = [_stay("R1", "101", "InHouse")]
    await client.post(f"{base}/hotel-os/sync", headers=admin_headers)

    token = (await client.post(f"{base}/gateways/GW/token", headers=admin_headers)).json()["token"]
    edge = {"Authorization": f"Bearer {token}"}
    measured = NOW.isoformat()
    await client.post(
        "/edge/v1/readings",
        json={
            "readings": [
                {"device_code": "101-TEMPERATURE", "value": 17.8, "measured_at": measured},
                {"device_code": "101-SETPOINT", "value": 21.0, "measured_at": measured},
                {"device_code": "103-TEMPERATURE", "value": 15.0, "measured_at": measured},
            ]
        },
        headers=edge,
    )
    await client.post(
        "/edge/v1/heartbeat",
        json={"sent_at": measured, "health": [{"device_code": "102-VALVE", "ok": False}]},
        headers=edge,
    )

    native = await client.get(f"{base}/faults", headers=admin_headers)
    kinds = {(f["kind"], f["unit_name"], f["severity"]) for f in native.json()["items"]}
    assert ("RoomTooCold", "101", "Today") in kinds
    assert ("DeviceFault", "102", "Attention") in kinds
    assert not any(k[0] == "RoomTooCold" and k[1] == "103" for k in kinds)  # vacant: eco, no fault
    assert not any(k[0] == "GatewayOffline" for k in kinds)

    url = "/api/integrations/hotel-os/v1/faults?property_code=HAM"
    assert (await client.get(url)).status_code == 401
    assert (await client.get(url, headers={"X-Api-Key": "wrong"})).status_code == 401
    served = await client.get(url, headers={"X-Api-Key": "inbox-key-0123456789"})
    assert served.status_code == 200
    contract = json.loads((CONTRACTS / "faults-response.json").read_text())
    assert set(served.json()) == set(contract)
    assert set(served.json()["items"][0]) == set(contract["items"][0])
    assert served.json()["property_code"] == "HAM"
    unknown = await client.get(
        "/api/integrations/hotel-os/v1/faults?property_code=NOPE",
        headers={"X-Api-Key": "inbox-key-0123456789"},
    )
    assert unknown.status_code == 404

    # Two minutes later without a heartbeat the gateway is offline.
    client._transport.app.dependency_overrides[get_clock] = lambda: type(  # type: ignore[attr-defined]
        "Later", (), {"now": staticmethod(lambda: NOW + timedelta(minutes=5))}
    )()
    later = await client.get(f"{base}/faults", headers=admin_headers)
    assert any(f["kind"] == "GatewayOffline" for f in later.json()["items"])
