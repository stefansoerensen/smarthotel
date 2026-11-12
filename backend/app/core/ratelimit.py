"""Simple in-memory sliding-window rate limiter."""

import time
from collections import deque
from collections.abc import Callable


class RateLimiter:
    """Allow at most ``max_calls`` per ``period_seconds`` per key."""

    def __init__(
        self, max_calls: int, period_seconds: float, now: Callable[[], float] = time.monotonic
    ) -> None:
        self._max = max_calls
        self._period = period_seconds
        self._now = now
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> bool:
        """Register a call; return False when the limit is exceeded."""
        current = self._now()
        window = self._hits.setdefault(key, deque())
        while window and current - window[0] >= self._period:
            window.popleft()
        if len(window) >= self._max:
            return False
        window.append(current)
        return True
