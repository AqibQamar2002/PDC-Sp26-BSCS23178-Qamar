"""
Mock LLM client.

This stands in for an external LLM provider (OpenAI / Anthropic / etc.).
A flag controls whether the "service" is healthy. When it is unhealthy,
calls hang for `hang_seconds` and then raise, exactly like an upstream
that has died at the network layer. That hang is what makes a *synchronous*
caller a single point of failure: every FastAPI worker thread that hits
this client gets stuck for the full timeout, until none are left to serve
real requests.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass


class LLMServiceDown(Exception):
    pass


@dataclass
class MockLLMClient:
    healthy: bool = True
    hang_seconds: float = 60.0
    healthy_latency_seconds: float = 0.05

    def crash(self, hang_seconds: float = 60.0) -> None:
        self.healthy = False
        self.hang_seconds = hang_seconds

    def heal(self) -> None:
        self.healthy = True

    async def complete(self, prompt: str) -> dict:
        if not self.healthy:
            await asyncio.sleep(self.hang_seconds)
            raise LLMServiceDown("upstream LLM did not respond")
        await asyncio.sleep(self.healthy_latency_seconds)
        return {
            "model": "mock-llm-1",
            "prompt": prompt,
            "completion": f"[mock answer to: {prompt[:60]}] (#{random.randint(1000, 9999)})",
        }


llm_client = MockLLMClient()
