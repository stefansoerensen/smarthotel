"""Injectable clock so business logic and tests control 'now'."""

from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    """Source of the current time."""

    def now(self) -> datetime:
        """Return the current aware UTC datetime."""
        ...


class SystemClock:
    """Real wall clock."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        return datetime.now(UTC)


class FixedClock:
    """Manually controlled clock for tests and simulations."""

    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        """Return the configured time."""
        return self._at

    def advance(self, delta: timedelta) -> None:
        """Move the clock forward by ``delta``."""
        self._at = self._at + delta

    def set(self, at: datetime) -> None:
        """Set the clock to ``at``."""
        self._at = at


def today_in(time_zone: str, clock: Clock) -> date:
    """Return the local calendar date in ``time_zone``."""
    return clock.now().astimezone(ZoneInfo(time_zone)).date()
