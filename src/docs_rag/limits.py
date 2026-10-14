"""Per-IP token-bucket rate limiting and a daily USD cost cap."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class _Bucket:
    tokens: float
    updated: float


class RateLimiter:
    """Token bucket per key (client IP). ``rate_per_minute`` refills, ``burst`` is the capacity."""

    def __init__(
        self,
        rate_per_minute: float,
        burst: int,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if rate_per_minute <= 0 or burst <= 0:
            raise ValueError("rate_per_minute and burst must be positive")
        self.rate_per_second = rate_per_minute / 60.0
        self.burst = float(burst)
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, cost: float = 1.0) -> tuple[bool, float]:
        """Return (allowed, retry_after_seconds)."""
        now = self._clock()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self.burst, updated=now)
                self._buckets[key] = bucket
            elapsed = max(0.0, now - bucket.updated)
            bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.rate_per_second)
            bucket.updated = now
            if bucket.tokens >= cost:
                bucket.tokens -= cost
                return True, 0.0
            retry_after = (cost - bucket.tokens) / self.rate_per_second
            return False, retry_after

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


class DailyCostCap:
    """Tracks USD spend per UTC day in memory and refuses work once the cap is reached."""

    def __init__(self, cap_usd: float, *, today: Callable[[], str] | None = None) -> None:
        self.cap_usd = cap_usd
        self._today = today or (lambda: datetime.now(UTC).strftime("%Y-%m-%d"))
        self._day = self._today()
        self._spent = 0.0
        self._lock = threading.Lock()

    def _roll(self) -> None:
        day = self._today()
        if day != self._day:
            self._day = day
            self._spent = 0.0

    @property
    def spent_today(self) -> float:
        with self._lock:
            self._roll()
            return self._spent

    @property
    def remaining(self) -> float:
        return max(0.0, self.cap_usd - self.spent_today)

    def allow(self) -> bool:
        with self._lock:
            self._roll()
            return self._spent < self.cap_usd

    def record(self, cost_usd: float) -> None:
        with self._lock:
            self._roll()
            self._spent += max(0.0, cost_usd)
