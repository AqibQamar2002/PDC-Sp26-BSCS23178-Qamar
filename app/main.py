"""
StudySync resilience demo - FastAPI app.

Endpoints:
    GET  /                  health check
    GET  /circuit/state     observability for the breaker
    POST /circuit/reset     manually reset the breaker (test helper)
    POST /admin/crash-llm   flip the mock LLM to "down"
    POST /admin/heal-llm    flip the mock LLM back to "up"

    POST /naive/llm         baseline -- no breaker, hangs when LLM is down
    POST /resilient/llm     fixed   -- breaker + fallback

Every response carries the mandatory  X-Student-ID  header (Part 3 rule #1).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .llm_client import llm_client
from .schemas import LLMRequest, LLMResponse

STUDENT_ID = "BSCS23178"


async def llm_fallback(prompt: str) -> dict:
    """Cheap, deterministic answer when the LLM is unreachable."""
    return {
        "model": "fallback-cache-v1",
        "prompt": prompt,
        "completion": (
            "Our AI tutor is temporarily unavailable. "
            "Here is a cached study tip: break the topic into 3 sub-questions "
            "and try the practice problems while we recover."
        ),
        "fallback": True,
        "reason": "llm_unavailable",
    }


breaker = CircuitBreaker(
    config=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=5.0,
        call_timeout=2.0,
        name="llm",
    ),
    fallback=lambda prompt, **_: llm_fallback(prompt),
)


app = FastAPI(title="StudySync Resilience Demo")


@app.middleware("http")
async def add_student_id_header(request: Request, call_next):
    """Mandatory custom header on every response (assignment rule #1)."""
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        response = JSONResponse(
            status_code=500,
            content={"detail": f"unhandled error: {exc}"},
        )
    response.headers["X-Student-ID"] = STUDENT_ID
    return response


@app.get("/")
async def root() -> dict:
    return {"app": "StudySync resilience demo", "student_id": STUDENT_ID}


@app.get("/circuit/state")
async def circuit_state() -> dict:
    m = breaker.metrics
    return {
        "state": m.state.value,
        "consecutive_failures": m.consecutive_failures,
        "total_calls": m.total_calls,
        "total_failures": m.total_failures,
        "total_short_circuits": m.total_short_circuits,
        "total_fallbacks": m.total_fallbacks,
    }


@app.post("/circuit/reset")
async def circuit_reset() -> dict:
    await breaker.reset()
    return {"ok": True, "state": breaker.state.value}


@app.post("/admin/crash-llm")
async def crash_llm(hang_seconds: float = 60.0) -> dict:
    llm_client.crash(hang_seconds=hang_seconds)
    return {"healthy": llm_client.healthy, "hang_seconds": llm_client.hang_seconds}


@app.post("/admin/heal-llm")
async def heal_llm() -> dict:
    llm_client.heal()
    return {"healthy": llm_client.healthy}


@app.post("/naive/llm", response_model=LLMResponse)
async def naive_llm(req: LLMRequest) -> LLMResponse:
    """
    Baseline - no protection. If the LLM hangs, this hangs too.
    This is the broken behavior described in the assignment.
    """
    result = await llm_client.complete(req.prompt)
    return LLMResponse(**result)


@app.post("/resilient/llm", response_model=LLMResponse)
async def resilient_llm(req: LLMRequest) -> LLMResponse:
    """
    Same operation, but routed through the circuit breaker. When the LLM
    misbehaves, the breaker trips and the fallback returns immediately.
    """
    result = await breaker.call(llm_client.complete, req.prompt)
    return LLMResponse(**result)
