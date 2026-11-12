"""The gateway against a fake control plane that can go down."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from edge_gateway.buffer import Buffer
from edge_gateway.bus import BusDevice, SimulatedBus
from edge_gateway.cloud import Cloud, CloudUnavailable
from edge_gateway.config import parse_scenario
from edge_gateway.gateway import Gateway

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts" / "edge-v1"


def contract(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text())


def device(code: str, room: str, key: str, kind: str, controllable: bool) -> dict:
    return {
        "code": code,
        "kind": kind,
        "protocol": "simulator",
        "address": None,
        "controllable": controllable,
        "room_code": room,
        "point_key": key,
    }


DEVICES = [
    device("101-TEMPERATURE", "101", "temperature", "temperature_sensor", False),
    device("101-SETPOINT", "101", "setpoint", "thermostat", True),
    device("101-WINDOW", "101", "window", "window_contact", False),
    device("101-VALVE", "101", "valve", "valve", True),
    device("101-SMOKE", "101", "smoke", "smoke_detector", False),
]


class FakeCloud:
    """An in-memory control plane speaking edge v1."""

    def __init__(self) -> None:
        self.up = True
        self.readings: list[dict] = []
        self.heartbeats: list[dict] = []
        self.queued: list[dict] = []
        self.acks: dict[str, dict] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        if not self.up:
            raise httpx.ConnectError("down", request=request)
        assert request.headers["authorization"] == "Bearer secret"
        path = request.url.path
        body = json.loads(request.content) if request.content else None
        if path == "/edge/v1/hello":
            return httpx.Response(
                200, json={"gateway_code": "GW", "property_code": "P", "devices": DEVICES}
            )
        if path == "/edge/v1/readings":
            assert set(body) == set(contract("readings-request.json"))
            assert set(body["readings"][0]) == set(contract("readings-request.json")["readings"][0])
            self.readings.extend(body["readings"])
            return httpx.Response(200, json={"accepted": len(body["readings"]), "ignored": 0})
        if path == "/edge/v1/heartbeat":
            assert set(body) == set(contract("heartbeat-request.json"))
            self.heartbeats.append(body)
            return httpx.Response(200, json={"status": "online"})
        if path == "/edge/v1/commands":
            taken, self.queued = self.queued, []
            return httpx.Response(200, json={"commands": taken})
        if path.startswith("/edge/v1/commands/") and path.endswith("/ack"):
            assert set(body) == set(contract("ack-request.json"))
            self.acks[path.split("/")[4]] = body
            return httpx.Response(200, json={"id": path.split("/")[4], "status": body["status"]})
        return httpx.Response(404)


class Clock:
    def __init__(self) -> None:
        self.at = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.at


@pytest.fixture
def setup(tmp_path: Path):
    fake = FakeCloud()
    clock = Clock()
    buses: list[SimulatedBus] = []

    def bus_factory(devices: list[dict]) -> SimulatedBus:
        bus = SimulatedBus([BusDevice(d["code"], d["room_code"], d["point_key"]) for d in devices])
        buses.append(bus)
        return bus

    cloud = Cloud(
        "https://cloud.test", "secret", httpx.Client(transport=httpx.MockTransport(fake.handler))
    )
    gateway = Gateway(cloud, bus_factory, Buffer(str(tmp_path / "edge.sqlite")), clock)
    gateway.start()
    return gateway, fake, clock, buses


def test_tick_heats_the_room_and_reports(setup) -> None:
    gateway, fake, clock, buses = setup
    gateway.tick(15)
    valve = [r for r in fake.readings if r["device_code"] == "101-VALVE"][-1]
    assert valve["value"] == 100.0
    assert fake.heartbeats[-1]["buffered"] == 0
    assert len(fake.heartbeats[-1]["health"]) == len(DEVICES)


def test_window_open_closes_the_valve(setup) -> None:
    gateway, fake, clock, buses = setup
    buses[0].rooms["101"].window = 1.0
    gateway.tick(5)
    assert buses[0].rooms["101"].valve == 0.0


def test_outage_buffers_and_delivers_with_original_times(setup) -> None:
    gateway, fake, clock, buses = setup
    fake.up = False
    clock.at += timedelta(minutes=1)
    outage_time = clock.at.isoformat()
    gateway.tick(1)
    assert gateway.online is False
    assert gateway.buffer.count() > 0
    fake.up = True
    clock.at += timedelta(minutes=1)
    gateway.tick(1)
    assert gateway.buffer.count() == 0
    delivered = [r["measured_at"] for r in fake.readings if r["device_code"] == "101-TEMPERATURE"]
    assert outage_time in delivered
    assert delivered == sorted(delivered)


def test_commands_are_executed_and_acknowledged(setup) -> None:
    gateway, fake, clock, buses = setup
    fake.queued = [
        {
            "id": "c1",
            "device_code": "101-SETPOINT",
            "value": 22.5,
            "created_at": clock.at.isoformat(),
        }
    ]
    gateway.tick(1)
    assert buses[0].rooms["101"].setpoint == 22.5
    assert fake.acks["c1"]["status"] == "done"


def test_command_for_a_read_only_device_is_refused(setup) -> None:
    gateway, fake, clock, buses = setup
    fake.queued = [
        {"id": "c2", "device_code": "101-SMOKE", "value": 1, "created_at": clock.at.isoformat()}
    ]
    gateway.tick(1)
    assert fake.acks["c2"] == {"status": "refused", "detail": "device is not controllable"}


def test_restart_without_cloud_uses_stored_configuration(setup, tmp_path: Path) -> None:
    gateway, fake, clock, buses = setup
    fake.up = False
    again = Gateway(
        gateway.cloud,
        lambda devices: SimulatedBus([]),
        Buffer(str(tmp_path / "edge.sqlite")),
        clock,
    )
    again.start()
    assert set(again.devices) == {d["code"] for d in DEVICES}


def test_first_start_without_cloud_fails(tmp_path: Path) -> None:
    fake = FakeCloud()
    fake.up = False
    cloud = Cloud(
        "https://cloud.test", "secret", httpx.Client(transport=httpx.MockTransport(fake.handler))
    )
    gateway = Gateway(
        cloud, lambda d: SimulatedBus([]), Buffer(str(tmp_path / "x.sqlite")), Clock()
    )
    with pytest.raises(CloudUnavailable):
        gateway.start()


def test_scenario_opens_a_window_at_its_minute() -> None:
    bus = SimulatedBus(
        [BusDevice("W", "101", "window")],
        scenario=parse_scenario("30:101:window:1, 90:101:window:0"),
    )
    bus.advance(29)
    assert bus.read("W") == 0.0
    bus.advance(2)
    assert bus.read("W") == 1.0
    bus.advance(60)
    assert bus.read("W") == 0.0
