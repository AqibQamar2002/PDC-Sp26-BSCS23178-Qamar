"""
Tests that simulate the failure described in the assignment and prove
the circuit breaker handles it gracefully.

Run with:
    pytest -v
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)
from app.llm_client import MockLLMClient


pytestmark = pytest.mark.asyncio


# ---------- helpers ----------


async def fallback_fn(prompt: str, **_) -> dict:
    return {"completion": "FALLBACK", "model": "cache", "fallback": True}


def make_breaker(**overrides) -> CircuitBreaker:
    defaults = dict(
        failure_threshold=3,
        recovery_timeout=0.5,
        call_timeout=0.3,
        name="test",
    )
    defaults.update(overrides)
    return CircuitBreaker(config=CircuitBreakerConfig(**defaults), fallback=fallback_fn)


# ---------- 1. baseline: a synchronous-style hang ----------


async def test_naive_call_blocks_when_llm_is_down():
    """
    This test demonstrates the BROKEN behaviour described in the assignment:
    without a breaker, calling a hung LLM blocks the caller for the full
    upstream timeout. We use a tiny `hang_seconds` so the test is fast,
    but the principle scales to the 60s real-world hang.
    """
    llm = MockLLMClient()
    llm.crash(hang_seconds=0.5)

    start = time.perf_counter()
    with pytest.raises(Exception):
        await llm.complete("hello")
    elapsed = time.perf_counter() - start

    assert elapsed >= 0.5, "naive call must block for the full hang window"


# ---------- 2. breaker trips after N consecutive failures ----------


async def test_breaker_trips_after_threshold_failures():
    breaker = make_breaker(failure_threshold=3)
    llm = MockLLMClient()
    llm.crash(hang_seconds=5.0)  # >> call_timeout, so each call times out

    for _ in range(3):
        result = await breaker.call(llm.complete, "anything")
        assert result["fallback"] is True

    assert breaker.state == CircuitState.OPEN
    assert breaker.metrics.consecutive_failures >= 3


# ---------- 3. once OPEN, calls short-circuit FAST ----------


async def test_open_breaker_short_circuits_immediately():
    breaker = make_breaker(failure_threshold=2)
    llm = MockLLMClient()
    llm.crash(hang_seconds=5.0)

    # trip the breaker
    for _ in range(2):
        await breaker.call(llm.complete, "x")
    assert breaker.state == CircuitState.OPEN

    # now a call must return in well under call_timeout - it never even
    # touches the downstream
    start = time.perf_counter()
    result = await breaker.call(llm.complete, "x")
    elapsed = time.perf_counter() - start

    assert result["fallback"] is True
    assert elapsed < 0.1, f"short-circuit should be near-instant, took {elapsed:.3f}s"
    assert breaker.metrics.total_short_circuits >= 1


# ---------- 4. breaker recovers via HALF_OPEN -> CLOSED ----------


async def test_breaker_recovers_when_service_heals():
    breaker = make_breaker(failure_threshold=2, recovery_timeout=0.3)
    llm = MockLLMClient()
    llm.crash(hang_seconds=5.0)

    for _ in range(2):
        await breaker.call(llm.complete, "x")
    assert breaker.state == CircuitState.OPEN

    # service recovers
    llm.heal()

    # not enough time has passed -> still OPEN, still short-circuits
    result = await breaker.call(llm.complete, "x")
    assert result["fallback"] is True

    # wait for recovery window, then a probe should succeed and CLOSE the breaker
    await asyncio.sleep(0.35)
    result = await breaker.call(llm.complete, "x")
    assert result.get("fallback") is not True
    assert breaker.state == CircuitState.CLOSED


# ---------- 5. concurrent flood: app stays responsive ----------


async def test_breaker_keeps_app_responsive_under_flood():
    """
    Fire 50 concurrent requests at a hung LLM. Without the breaker every
    request would wait the full upstream timeout. With the breaker, the
    *aggregate* time stays bounded because once it trips, all later
    requests short-circuit.
    """
    breaker = make_breaker(failure_threshold=3, call_timeout=0.2)
    llm = MockLLMClient()
    llm.crash(hang_seconds=5.0)

    start = time.perf_counter()
    results = await asyncio.gather(
        *[breaker.call(llm.complete, f"q{i}") for i in range(50)]
    )
    elapsed = time.perf_counter() - start

    assert all(r["fallback"] is True for r in results)
    # 50 sequential 0.2s timeouts would be 10s. With short-circuits we
    # expect well under 2s.
    assert elapsed < 2.0, f"breaker failed to keep app responsive: {elapsed:.2f}s"
