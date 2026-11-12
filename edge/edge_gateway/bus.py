"""The field bus as the gateway sees it, and a simulated bus for tests and demos.

The simulated bus is the *building*: room physics without a controller. The controller is the
gateway's job (``rules.py``). Real connectors (KNX/IP, BACnet/IP, Modbus) implement the same
interface once real hardware is allowed (hub b32/a16/b08).
"""

from dataclasses import dataclass
from typing import Protocol

from edge_gateway.config import ScenarioEvent

HEATING_RATE_K_PER_H = 2.5
LOSS_PER_H = 0.06
WINDOW_LOSS_FACTOR = 8.0
HEAT_POWER_KW = 1.2
MAX_STEP_MINUTES = 5.0


class Bus(Protocol):
    """What the gateway needs from a field bus."""

    def read(self, device_code: str) -> float | None:
        """Current value of a device, or None if it does not answer."""

    def write(self, device_code: str, value: float) -> None:
        """Set a device."""

    def healthy(self, device_code: str) -> bool:
        """Whether the device answers."""

    def advance(self, minutes: float) -> None:
        """Let time pass (only meaningful for a simulated bus)."""


@dataclass
class SimRoom:
    """Physical state of one simulated room."""

    temperature: float = 18.0
    setpoint: float = 21.0
    window: float = 0.0
    presence: float = 0.0
    valve: float = 0.0
    light: float = 0.0
    heat_meter: float = 0.0


@dataclass(frozen=True)
class BusDevice:
    """A device on the bus: which room and which point it belongs to."""

    code: str
    room: str
    key: str


class SimulatedBus:
    """Deterministic rooms on a fake bus."""

    def __init__(
        self,
        devices: list[BusDevice],
        *,
        outdoor: float = 5.0,
        scenario: list[ScenarioEvent] | None = None,
        faulty: frozenset[str] = frozenset(),
    ) -> None:
        self.devices = {d.code: d for d in devices}
        self.rooms: dict[str, SimRoom] = {d.room: SimRoom() for d in devices}
        self.outdoor = outdoor
        self.scenario = list(scenario or [])
        self.faulty = faulty
        self.minute = 0.0

    def read(self, device_code: str) -> float | None:
        """Value of the device's point in its room."""
        device = self.devices.get(device_code)
        if device is None or device_code in self.faulty:
            return None
        return float(getattr(self.rooms[device.room], device.key, 0.0))

    def write(self, device_code: str, value: float) -> None:
        """Set the device's point in its room."""
        device = self.devices[device_code]
        if hasattr(self.rooms[device.room], device.key):
            setattr(self.rooms[device.room], device.key, value)

    def healthy(self, device_code: str) -> bool:
        """A device answers unless it is listed as faulty."""
        return device_code in self.devices and device_code not in self.faulty

    def advance(self, minutes: float) -> None:
        """Run scenario events that are due, then room physics in steps of five minutes."""
        end = self.minute + minutes
        while self.scenario and self.scenario[0].minute <= end:
            event = self.scenario.pop(0)
            room = self.rooms.get(event.room)
            if room is not None and hasattr(room, event.key):
                setattr(room, event.key, event.value)
        remaining = minutes
        while remaining > 1e-9:
            dt = min(MAX_STEP_MINUTES, remaining)
            for room in self.rooms.values():
                hours = dt / 60.0
                loss = LOSS_PER_H * (WINDOW_LOSS_FACTOR if room.window >= 0.5 else 1.0)
                room.temperature += (
                    HEATING_RATE_K_PER_H * room.valve / 100.0 * hours
                    - loss * (room.temperature - self.outdoor) * hours
                )
                room.heat_meter += HEAT_POWER_KW * room.valve / 100.0 * hours
            remaining -= dt
        self.minute = end
