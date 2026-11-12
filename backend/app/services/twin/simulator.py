"""A deterministic room simulator.

Pure functions only: the same state, minutes and outdoor temperature always give the same result.
It contains a proportional room controller as a stand-in for the controller in the building; the
edge's local rules replace it for real rooms (SB2, ADR-0005).
"""

from dataclasses import dataclass, replace

HEATING_RATE_K_PER_H = 2.5  # temperature rise per hour at a fully open valve, before losses
LOSS_PER_H = 0.06  # share of the indoor/outdoor difference lost per hour, window closed
WINDOW_LOSS_FACTOR = 8.0  # an open window multiplies the loss
VALVE_GAIN = 60.0  # % valve opening per kelvin below the set point
HEAT_POWER_KW = 1.2  # thermal power of the room's radiator at a fully open valve
MAX_STEP_MINUTES = 5.0

START_TEMPERATURE = 18.0
START_SETPOINT = 21.0


@dataclass(frozen=True)
class RoomState:
    """What the simulator knows about a room."""

    temperature: float
    setpoint: float
    window: float
    presence: float
    valve: float
    heat_meter: float


def controller(state: RoomState) -> float:
    """Valve opening in %: closed with an open window, else proportional to the shortfall."""
    if state.window >= 0.5:
        return 0.0
    return max(0.0, min(100.0, (state.setpoint - state.temperature) * VALVE_GAIN))


def _tick(state: RoomState, minutes: float, outdoor: float) -> RoomState:
    valve = controller(state)
    hours = minutes / 60.0
    loss = LOSS_PER_H * (WINDOW_LOSS_FACTOR if state.window >= 0.5 else 1.0)
    temperature = (
        state.temperature
        + HEATING_RATE_K_PER_H * valve / 100.0 * hours
        - loss * (state.temperature - outdoor) * hours
    )
    heat = HEAT_POWER_KW * valve / 100.0 * hours
    return replace(
        state,
        temperature=temperature,
        valve=valve,
        heat_meter=state.heat_meter + heat,
    )


def step(state: RoomState, *, minutes: float, outdoor: float) -> RoomState:
    """Advance a room by ``minutes``, in sub-steps of at most five minutes."""
    remaining = float(minutes)
    current = state
    while remaining > 1e-9:
        dt = min(MAX_STEP_MINUTES, remaining)
        current = _tick(current, dt, outdoor)
        remaining -= dt
    return replace(
        current,
        temperature=round(current.temperature, 2),
        valve=round(current.valve, 1),
        heat_meter=round(current.heat_meter, 3),
    )
