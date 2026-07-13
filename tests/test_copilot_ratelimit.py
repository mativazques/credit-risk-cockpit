"""Unit tests for the rate limiter (C3.3 / L2).

Two bounds make the shared free daily quota last: a per-key token bucket (one visitor
can't burst) and a global daily counter (the whole demo can't exceed a safe ceiling).
Time and date are injected so the behavior is deterministic.
"""
from copilot.ratelimit import RateLimiter


def _limiter(**kw):
    defaults = dict(capacity=2, refill_per_sec=1.0, daily_limit=100,
                    now=lambda: 0.0, today=lambda: "2026-01-01")
    defaults.update(kw)
    return RateLimiter(**defaults)


def test_per_key_burst_is_capped_then_refills():
    clock = [0.0]
    rl = _limiter(now=lambda: clock[0])
    assert rl.allow("ip") is True
    assert rl.allow("ip") is True
    assert rl.allow("ip") is False       # bucket empty
    clock[0] = 1.0                        # one token refilled
    assert rl.allow("ip") is True
    assert rl.allow("ip") is False


def test_refill_never_exceeds_capacity():
    clock = [0.0]
    rl = _limiter(now=lambda: clock[0])
    clock[0] = 1000.0                     # long idle
    assert rl.allow("ip") is True
    assert rl.allow("ip") is True
    assert rl.allow("ip") is False        # capped at capacity=2, not 1000


def test_keys_are_independent():
    rl = _limiter()
    assert rl.allow("a") and rl.allow("a")
    assert rl.allow("a") is False
    assert rl.allow("b") is True          # different key, own bucket


def test_global_daily_limit_blocks_across_keys():
    rl = _limiter(capacity=100, refill_per_sec=100.0, daily_limit=2)
    assert rl.allow("a") is True
    assert rl.allow("b") is True
    assert rl.allow("c") is False         # global cap reached regardless of key


def test_blocked_by_bucket_does_not_consume_daily_budget():
    rl = _limiter(capacity=1, refill_per_sec=0.0, daily_limit=5)
    assert rl.allow("ip") is True
    assert rl.allow("ip") is False        # bucket empty
    # daily budget only spent the one allowed call
    for k in ("a", "b", "c", "d"):
        assert rl.allow(k) is True
    assert rl.allow("e") is False         # now the 5-daily cap is hit


def test_daily_counter_resets_on_a_new_day():
    day = ["2026-01-01"]
    rl = _limiter(capacity=100, refill_per_sec=100.0, daily_limit=1, today=lambda: day[0])
    assert rl.allow("ip") is True
    assert rl.allow("ip") is False
    day[0] = "2026-01-02"
    assert rl.allow("ip") is True
