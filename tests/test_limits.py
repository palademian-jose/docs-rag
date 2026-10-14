from __future__ import annotations

import pytest

from docs_rag.limits import DailyCostCap, RateLimiter


def test_rate_limiter_burst_then_refill() -> None:
    now = [0.0]
    limiter = RateLimiter(rate_per_minute=60, burst=3, clock=lambda: now[0])
    assert [limiter.allow("ip")[0] for _ in range(3)] == [True, True, True]
    allowed, retry_after = limiter.allow("ip")
    assert not allowed and retry_after == pytest.approx(1.0)
    now[0] += 1.0  # one token refilled at 1/s
    assert limiter.allow("ip")[0] is True
    assert limiter.allow("ip")[0] is False
    # other clients have their own bucket
    assert limiter.allow("other")[0] is True
    limiter.reset()
    assert limiter.allow("ip")[0] is True


def test_rate_limiter_caps_at_burst() -> None:
    now = [0.0]
    limiter = RateLimiter(rate_per_minute=600, burst=2, clock=lambda: now[0])
    now[0] += 1000
    assert limiter.allow("ip")[0] and limiter.allow("ip")[0]
    assert not limiter.allow("ip")[0]
    with pytest.raises(ValueError):
        RateLimiter(0, 1)


def test_daily_cost_cap_rolls_over_at_midnight() -> None:
    day = ["2026-10-15"]
    cap = DailyCostCap(1.0, today=lambda: day[0])
    assert cap.allow() and cap.remaining == 1.0
    cap.record(0.6)
    assert cap.allow() and cap.spent_today == pytest.approx(0.6)
    cap.record(0.5)
    assert not cap.allow() and cap.remaining == 0.0
    day[0] = "2026-10-16"
    assert cap.allow() and cap.spent_today == 0.0
    cap.record(-5)  # negative costs are ignored
    assert cap.spent_today == 0.0
