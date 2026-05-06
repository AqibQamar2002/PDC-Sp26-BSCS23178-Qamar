Aqib Bin Qamar - BSCS23178

# StudySync Resilience Demo - Circuit Breaker for the LLM Call

This repository implements **Part 3** of the PDC Assignment 2: a working
fix for **Problem 3 (Fault Tolerance)** in a FastAPI backend.

A `MockLLMClient` simulates an external LLM that hangs for 60s when it
goes down. Without protection, every FastAPI request hitting that client
gets stuck and the whole app becomes unresponsive. The fix is a
three-state **Circuit Breaker** (`CLOSED -> OPEN -> HALF_OPEN`) with a
**fallback** response, plus a per-call timeout so a single hung upstream
can never pin a worker.

The mandatory `X-Student-ID` middleware header is added to **every**
response (see `app/main.py`).

## Project layout

```
app/
  main.py             FastAPI app + X-Student-ID middleware + endpoints
  circuit_breaker.py  CLOSED / OPEN / HALF_OPEN breaker with fallback
  llm_client.py       Mock LLM (can be flipped to "down")
  schemas.py          Pydantic request/response models
tests/
  test_circuit_breaker.py   pytest suite that simulates the failure
scripts/
  demo.py             End-to-end script for the demo video
report/
  report.md           Part 1 + Part 2 written report (Markdown)
  report.tex          Part 1 + Part 2 written report (LaTeX)
```

## Setup

Tested on Python 3.11 / 3.12.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

The app will be on http://127.0.0.1:8000. Try:

```bash
curl -i http://127.0.0.1:8000/
# response includes:  X-Student-ID: BSCS23178
```

## Run the tests (proves the fix works)

```bash
pytest -v
```

Five tests run:

1. `test_naive_call_blocks_when_llm_is_down` - shows the **broken**
   baseline: a naive call hangs for the full upstream timeout.
2. `test_breaker_trips_after_threshold_failures` - breaker opens after
   N consecutive failures.
3. `test_open_breaker_short_circuits_immediately` - once OPEN, calls
   return in < 100ms via the fallback.
4. `test_breaker_recovers_when_service_heals` - HALF_OPEN probe closes
   the breaker once the LLM is healthy again.
5. `test_breaker_keeps_app_responsive_under_flood` - 50 concurrent
   requests against a hung LLM finish in under 2s instead of 10s+.

## Run the live demo (used in the video)

In one terminal:

```bash
uvicorn app.main:app --reload
```

In another:

```bash
python scripts/demo.py
```

The script walks through:

1. Health check + showing the `X-Student-ID` header.
2. `POST /admin/crash-llm` to flip the mock LLM to "down".
3. `POST /naive/llm` x3 - hangs / times out (the broken behaviour).
4. `POST /resilient/llm` x6 - first 3 fall back with a normal response,
   the breaker trips, the rest short-circuit instantly.
5. `POST /admin/heal-llm`, wait `recovery_timeout`, then a single
   `/resilient/llm` call closes the breaker via HALF_OPEN.

## Endpoints

| Method | Path                  | Purpose                                                 |
|--------|-----------------------|---------------------------------------------------------|
| GET    | `/`                   | Health + identity                                       |
| POST   | `/naive/llm`          | Baseline call - **no** breaker (used to show the bug)   |
| POST   | `/resilient/llm`      | Same call routed through the breaker (the **fix**)      |
| GET    | `/circuit/state`      | Inspect breaker state and counters                      |
| POST   | `/circuit/reset`      | Reset breaker to CLOSED (test helper)                   |
| POST   | `/admin/crash-llm`    | Force the mock LLM to "down"                            |
| POST   | `/admin/heal-llm`     | Bring the mock LLM back up                              |

## How the breaker works (one paragraph)

It wraps every downstream call in `asyncio.wait_for(..., call_timeout)`,
counts consecutive failures, and once `failure_threshold` is hit, moves
to `OPEN`. In `OPEN` the breaker does not call the downstream at all and
returns the fallback immediately. After `recovery_timeout` seconds in
`OPEN`, the next call is allowed through as a `HALF_OPEN` probe; if it
succeeds, the breaker returns to `CLOSED`, otherwise it goes back to
`OPEN` for another window.
