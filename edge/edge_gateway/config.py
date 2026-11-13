"""Gateway settings from the environment."""

import os
from dataclasses import dataclass, field


class ConfigError(Exception):
    """A missing or invalid ``EDGE_*`` variable; the message names it."""


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
        """Read ``EDGE_*`` variables; raise ConfigError naming every missing or invalid one."""
        missing = [name for name in ("EDGE_CLOUD_URL", "EDGE_TOKEN") if not os.environ.get(name)]
        if missing:
            raise ConfigError(f"Missing variables: {', '.join(missing)}")
        url = os.environ["EDGE_CLOUD_URL"].strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        def number(name: str, default: str) -> float:
            raw = os.environ.get(name, default)
            try:
                return float(raw.replace(",", "."))
            except ValueError:
                raise ConfigError(f"{name} must be a number, got {raw!r}") from None

        try:
            scenario = parse_scenario(os.environ.get("EDGE_SCENARIO", ""))
        except ValueError:
            raise ConfigError(
                "EDGE_SCENARIO must look like 30:101:window:1,90:101:window:0"
            ) from None
        return cls(
            cloud_url=url,
            token=os.environ["EDGE_TOKEN"].strip(),
            tick_seconds=number("EDGE_TICK_SECONDS", "15"),
            simulated_minutes_per_tick=number("EDGE_SIM_MINUTES_PER_TICK", "0.25"),
            outdoor=number("EDGE_OUTDOOR", "5"),
            buffer_path=os.environ.get("EDGE_BUFFER_PATH", "/data/edge.sqlite"),
            scenario=scenario,
            faulty_devices=frozenset(
                c.strip() for c in os.environ.get("EDGE_FAULTY_DEVICES", "").split(",") if c.strip()
            ),
        )
