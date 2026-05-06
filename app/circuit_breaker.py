"""
Async Circuit Breaker.

States:
    CLOSED    -> normal operation; failures are counted.
    OPEN      -> calls are short-circuited and the fallback is returned
                 immediately, without ever touching the downstream service.
    HALF_OPEN -> after `recovery_timeout` seconds in OPEN, a single probe is
                 allowed through. Success closes the breaker; failure re-opens
                 it for another `recovery_timeout` window.

The breaker also enforces a per-call timeout so that a hung downstream
(e.g. an LLM API that takes 60s to time out at the TCP layer) cannot pin
a FastAPI worker thread.
"""

from __future__ import annotations

import asyncio
import enum
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


class CircuitState(str, enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(Exception):
    """Raised internally when a call is short-circuited."""


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3          # consecutive failures before tripping
    recovery_timeout: float = 5.0       # seconds OPEN before trying HALF_OPEN
    call_timeout: float = 2.0           # per-call timeout in seconds
    name: str = "default"


@dataclass
class CircuitBreakerMetrics:
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_short_circuits: int = 0
    total_fallbacks: int = 0
    opened_at: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)


class CircuitBreaker:
    """Async circuit breaker with a fallback callable."""

    def __init__(
        self,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable[..., Awaitable[Any]]] = None,
    ) -> None:
        self.config = config or CircuitBreakerConfig()
        self._fallback = fallback
        self._metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._metrics.state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        return self._metrics

    async def _transition(self, new_state: CircuitState) -> None:
        if self._metrics.state == new_state:
            return
        self._metrics.state = new_state
        self._metrics.last_state_change = time.time()
        if new_state == CircuitState.OPEN:
            self._metrics.opened_at = time.time()
        if new_state == CircuitState.CLOSED:
            self._metrics.consecutive_failures = 0
            self._metrics.opened_at = None

    async def _maybe_half_open(self) -> None:
        """If we've waited long enough in OPEN, allow a probe."""
        if self._metrics.state != CircuitState.OPEN:
            return
        if self._metrics.opened_at is None:
            return
        if time.time() - self._metrics.opened_at >= self.config.recovery_timeout:
            await self._transition(CircuitState.HALF_OPEN)

    async def call(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Run `func(*args, **kwargs)` through the breaker.
        Returns the function's result, or the fallback's result if the
        breaker is open / the call fails.
        """
        async with self._lock:
            self._metrics.total_calls += 1
            await self._maybe_half_open()
            current_state = self._metrics.state

        if current_state == CircuitState.OPEN:
            async with self._lock:
                self._metrics.total_short_circuits += 1
            return await self._run_fallback(*args, **kwargs)

        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.call_timeout,
            )
        except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
            await self._record_failure()
            return await self._run_fallback(*args, _error=exc, **kwargs)

        await self._record_success()
        return result

    async def _record_success(self) -> None:
        async with self._lock:
            if self._metrics.state == CircuitState.HALF_OPEN:
                await self._transition(CircuitState.CLOSED)
            self._metrics.consecutive_failures = 0

    async def _record_failure(self) -> None:
        async with self._lock:
            self._metrics.total_failures += 1
            self._metrics.consecutive_failures += 1
            if self._metrics.state == CircuitState.HALF_OPEN:
                await self._transition(CircuitState.OPEN)
                return
            if (
                self._metrics.state == CircuitState.CLOSED
                and self._metrics.consecutive_failures
                >= self.config.failure_threshold
            ):
                await self._transition(CircuitState.OPEN)

    async def _run_fallback(self, *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            self._metrics.total_fallbacks += 1
        kwargs.pop("_error", None)
        if self._fallback is None:
            return {
                "fallback": True,
                "reason": "circuit_open_or_call_failed",
                "circuit_state": self._metrics.state.value,
            }
        return await self._fallback(*args, **kwargs)

    async def reset(self) -> None:
        """Force the breaker back to CLOSED. Useful for tests."""
        async with self._lock:
            self._metrics = CircuitBreakerMetrics()
