"""Gateway settings from the environment."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScenarioEvent:
    """A simulated change on the bus: at ``minute``, set ``key`` of ``room`` to ``value``."""

    minute: float
    room: str
    key: str
    value: float


def parse_scenario(text: str) -> list[ScenarioEvent]:
    """Parse ``"30:101:window:1, 90:101:window:0"`` into events, sorted by minute."""
    events = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        minute, room, key, value = part.split(":")
        events.append(ScenarioEvent(float(minute), room, key, float(value)))
    return sorted(events, key=lambda e: e.minute)


@dataclass(frozen=True)
class Settings:
    """Runtime configuration of one gateway."""

    cloud_url: str
    token: str
    tick_seconds: float = 15.0
    simulated_minutes_per_tick: float = 0.25
    outdoor: float = 5.0
    buffer_path: str = "/data/edge.sqlite"
    scenario: list[ScenarioEvent] = field(default_factory=list)
    faulty_devices: frozenset[str] = frozenset()

    @classmethod
    def from_env(cls) -> "Settings":
        """Read ``EDGE_*`` variables."""
        return cls(
            cloud_url=os.environ["EDGE_CLOUD_URL"].rstrip("/"),
            token=os.environ["EDGE_TOKEN"],
            tick_seconds=float(os.environ.get("EDGE_TICK_SECONDS", "15")),
            simulated_minutes_per_tick=float(os.environ.get("EDGE_SIM_MINUTES_PER_TICK", "0.25")),
            outdoor=float(os.environ.get("EDGE_OUTDOOR", "5")),
            buffer_path=os.environ.get("EDGE_BUFFER_PATH", "/data/edge.sqlite"),
            scenario=parse_scenario(os.environ.get("EDGE_SCENARIO", "")),
            faulty_devices=frozenset(
                c.strip() for c in os.environ.get("EDGE_FAULTY_DEVICES", "").split(",") if c.strip()
            ),
        )
