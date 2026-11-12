"""Local rules that run on the gateway every tick, with or without the cloud.

Deterministic (hub d12): a proportional room controller, "window open → heating off" and frost
protection. Rules only ever write to controllable devices (ADR-0003).
"""

VALVE_GAIN = 60.0
FROST_LIMIT = 7.0


def valve_for(temperature: float | None, setpoint: float | None, window: float | None) -> float:
    """Valve opening in % for a room."""
    if temperature is None:
        return 0.0
    if temperature < FROST_LIMIT:
        return 100.0
    if window is not None and window >= 0.5:
        return 0.0
    target = setpoint if setpoint is not None else 21.0
    return max(0.0, min(100.0, (target - temperature) * VALVE_GAIN))


def room_writes(values: dict[str, float | None], controllable: set[str]) -> dict[str, float]:
    """What the rules want to set in one room, limited to controllable points.

    ``values`` maps point keys (``temperature``, ``setpoint``, ``window``, ``valve`` …) to their
    current values; ``controllable`` lists the keys whose devices may be written.
    """
    writes: dict[str, float] = {}
    if "valve" in controllable:
        writes["valve"] = round(
            valve_for(values.get("temperature"), values.get("setpoint"), values.get("window")), 1
        )
    return writes
