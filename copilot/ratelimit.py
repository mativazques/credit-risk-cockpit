"""Rate limiting (C3.3 / L2) — make the shared free daily budget last.

Two bounds: a per-key token bucket (a single visitor can't burst through the quota) and
a global daily counter kept under the AI Studio free-tier ceiling. In-memory and
single-process — fine for a scale-to-zero Cloud Run demo; a distributed store would be
the production upgrade. Time and date are injected for deterministic testing.
"""
from __future__ import annotations

import time
from datetime import date
from typing import Callable


def _default_today() -> str:
    return date.today().isoformat()


class RateLimiter:
    def __init__(
        self,
        capacity: int,
        refill_per_sec: float,
        daily_limit: int,
        now: Callable[[], float] = time.monotonic,
        today: Callable[[], str] = _default_today,
    ):
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self.daily_limit = daily_limit
        self._now = now
        self._today = today
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, updated_at)
        self._day = today()
        self._daily_count = 0

    def reset(self) -> None:
        self._buckets.clear()
        self._day = self._today()
        self._daily_count = 0

    def _roll_day(self) -> None:
        today = self._today()
        if today != self._day:
            self._day = today
            self._daily_count = 0

    def allow(self, key: str) -> bool:
        self._roll_day()
        if self._daily_count >= self.daily_limit:
            return False
        if not self._take(key):
            return False
        self._daily_count += 1
        return True

    def _take(self, key: str) -> bool:
        now = self._now()
        tokens, updated = self._buckets.get(key, (float(self.capacity), now))
        tokens = min(self.capacity, tokens + (now - updated) * self.refill_per_sec)
        if tokens < 1:
            self._buckets[key] = (tokens, now)
            return False
        self._buckets[key] = (tokens - 1, now)
        return True
