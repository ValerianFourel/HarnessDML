"""Round-robin fan-out over several OpenAI-compatible endpoints.

JUPITER one_gpu serving mode runs 4 independent vLLM servers per node
(ports 8001–8004, §7); this client spreads rollout calls across them.
"""

from __future__ import annotations

from .base import ChatResult


class MultiEndpointClient:
    def __init__(self, clients: list):
        if not clients:
            raise ValueError("need at least one client")
        self.clients = list(clients)
        self._i = 0

    async def chat(self, messages, *, temperature, top_p, max_tokens, seed) -> ChatResult:
        client = self.clients[self._i % len(self.clients)]
        self._i += 1
        return await client.chat(
            messages, temperature=temperature, top_p=top_p,
            max_tokens=max_tokens, seed=seed,
        )

    async def aclose(self) -> None:
        for c in self.clients:
            if hasattr(c, "aclose"):
                await c.aclose()
