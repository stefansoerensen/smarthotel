"""One gateway tick: bus, local rules, buffer, cloud — in that order, so rooms never wait for it."""

import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime

from edge_gateway.buffer import Buffer
from edge_gateway.bus import Bus
from edge_gateway.cloud import Cloud, CloudUnavailable
from edge_gateway.rules import room_writes

logger = logging.getLogger(__name__)

BATCH = 500


class Gateway:
    """Runs one property's rooms and talks to the control plane when it can."""

    def __init__(
        self,
        cloud: Cloud,
        bus_factory: Callable[[list[dict]], Bus],
        buffer: Buffer,
        now: Callable[[], datetime],
    ) -> None:
        self.cloud = cloud
        self.bus_factory = bus_factory
        self.buffer = buffer
        self.now = now
        self.devices: dict[str, dict] = {}
        self.bus: Bus | None = None
        self.pending_acks: list[tuple[str, str, str | None]] = []
        self.online = False

    def start(self) -> None:
        """Load the configuration from the cloud, or the last stored one when it is unreachable."""
        try:
            hello = self.cloud.hello()
            self.buffer.save_config(hello)
            self.online = True
        except CloudUnavailable:
            hello = self.buffer.load_config()
            if hello is None:
                raise
            logger.warning("cloud unreachable at start; running with the stored configuration")
        self.devices = {d["code"]: d for d in hello["devices"]}
        self.bus = self.bus_factory(hello["devices"])

    def tick(self, minutes: float) -> None:
        """Advance the bus, apply rules, buffer readings, then sync with the cloud."""
        assert self.bus is not None, "start() first"
        self.bus.advance(minutes)
        self._apply_rules()
        stamp = self.now().isoformat()
        readings = []
        for code in self.devices:
            value = self.bus.read(code)
            if value is not None:
                readings.append((code, round(value, 3), stamp))
        self.buffer.add(readings)
        self._sync()

    def _apply_rules(self) -> None:
        by_room: dict[str, dict[str, dict]] = defaultdict(dict)
        for device in self.devices.values():
            if device.get("room_code") and device.get("point_key"):
                by_room[device["room_code"]][device["point_key"]] = device
        for points in by_room.values():
            values = {key: self.bus.read(d["code"]) for key, d in points.items()}
            controllable = {key for key, d in points.items() if d["controllable"]}
            for key, value in room_writes(values, controllable).items():
                self.bus.write(points[key]["code"], value)

    def _sync(self) -> None:
        try:
            self._flush()
            self.cloud.heartbeat(
                {
                    "sent_at": self.now().isoformat(),
                    "buffered": self.buffer.count(),
                    "health": [
                        {"device_code": code, "ok": self.bus.healthy(code)} for code in self.devices
                    ],
                }
            )
            self._retry_acks()
            for command in self.cloud.commands():
                self._execute(command)
            self.online = True
        except CloudUnavailable as exc:
            if self.online:
                logger.warning("cloud unreachable, buffering: %s", exc)
            self.online = False

    def _flush(self) -> None:
        while True:
            batch = self.buffer.peek(BATCH)
            if not batch:
                return
            self.cloud.send_readings(
                [
                    {"device_code": r.device_code, "value": r.value, "measured_at": r.measured_at}
                    for r in batch
                ]
            )
            self.buffer.remove([r.id for r in batch])

    def _execute(self, command: dict) -> None:
        device = self.devices.get(command["device_code"])
        if device is None:
            status, detail = "failed", "unknown device"
        elif not device["controllable"]:
            status, detail = "refused", "device is not controllable"
        else:
            try:
                self.bus.write(device["code"], float(command["value"]))
                status, detail = "done", None
            except Exception as exc:  # noqa: BLE001 - any bus error becomes a failed command
                status, detail = "failed", str(exc)[:500]
        self.pending_acks.append((command["id"], status, detail))
        self._retry_acks()

    def _retry_acks(self) -> None:
        while self.pending_acks:
            command_id, status, detail = self.pending_acks[0]
            self.cloud.ack(command_id, status, detail)
            self.pending_acks.pop(0)
