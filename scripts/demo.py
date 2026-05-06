"""
Live demo script for the 2-minute video.

Run the server first:
    uvicorn app.main:app --reload

Then run this script:
    python scripts/demo.py

It does, in order:
    1. health check (shows X-Student-ID header)
    2. crashes the mock LLM
    3. fires 5 requests at /naive/llm  -> shows the hang / 500s
    4. fires 5 requests at /resilient/llm -> shows breaker trip + fallback
    5. heals the LLM, waits, shows /resilient/llm recovers via HALF_OPEN
"""

from __future__ import annotations

import asyncio
import time

import httpx

BASE = "http://127.0.0.1:8000"


def banner(text: str) -> None:
    line = "=" * 70
    print(f"\n{line}\n{text}\n{line}")


async def show_header(client: httpx.AsyncClient) -> None:
    r = await client.get(f"{BASE}/")
    print(f"GET / -> {r.status_code}")
    print(f"  X-Student-ID header = {r.headers.get('X-Student-ID')!r}")
    print(f"  body = {r.json()}")


async def hit(client: httpx.AsyncClient, path: str, prompt: str, timeout: float):
    start = time.perf_counter()
    try:
        r = await client.post(f"{BASE}{path}", json={"prompt": prompt}, timeout=timeout)
        elapsed = time.perf_counter() - start
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
        return {"status": r.status_code, "elapsed": elapsed, "body": body}
    except Exception as e:  # noqa: BLE001
        elapsed = time.perf_counter() - start
        return {"status": "ERROR", "elapsed": elapsed, "body": repr(e)}


async def main() -> None:
    async with httpx.AsyncClient() as client:
        banner("STEP 1  -  health + custom header")
        await show_header(client)

        banner("STEP 2  -  crash the mock LLM (hang_seconds=5)")
        r = await client.post(f"{BASE}/admin/crash-llm", params={"hang_seconds": 5})
        print(r.json())
        await client.post(f"{BASE}/circuit/reset")

        banner("STEP 3  -  /naive/llm  (no breaker)  - watch this hang/timeout")
        for i in range(3):
            res = await hit(client, "/naive/llm", f"naive-{i}", timeout=3.0)
            print(f"  naive #{i}: status={res['status']} elapsed={res['elapsed']:.2f}s")

        banner("STEP 4  -  /resilient/llm  (with circuit breaker)")
        for i in range(6):
            res = await hit(client, "/resilient/llm", f"resilient-{i}", timeout=3.0)
            preview = res["body"]
            if isinstance(preview, dict):
                preview = {k: preview.get(k) for k in ("fallback", "completion", "model")}
            print(f"  resilient #{i}: status={res['status']} elapsed={res['elapsed']:.2f}s  body={preview}")
        state = (await client.get(f"{BASE}/circuit/state")).json()
        print(f"  circuit state -> {state}")

        banner("STEP 5  -  heal the LLM and wait for HALF_OPEN probe to recover")
        await client.post(f"{BASE}/admin/heal-llm")
        print("waiting 6s for recovery_timeout to elapse...")
        await asyncio.sleep(6)
        res = await hit(client, "/resilient/llm", "post-heal", timeout=3.0)
        print(f"  post-heal: status={res['status']} elapsed={res['elapsed']:.2f}s")
        print(f"  body={res['body']}")
        state = (await client.get(f"{BASE}/circuit/state")).json()
        print(f"  circuit state -> {state}")


if __name__ == "__main__":
    asyncio.run(main())
