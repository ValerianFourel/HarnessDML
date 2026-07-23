"""Deterministic mock backend — the ONLY backend tests use (§8).

A responder callable receives (messages, seed) and returns the assistant
text; token counts are synthesized deterministically from character counts.
`scripted()` builds a responder from a fixed list of turns keyed per
conversation, for loop tests that need multi-turn trajectories.
"""

from __future__ import annotations

from typing import Callable

from .base import ChatResult

Responder = Callable[[list[dict], int], str]


class MockClient:
    def __init__(self, responder: Responder, fail_times: int = 0):
        self.responder = responder
        self.calls: list[list[dict]] = []
        self._fail_times = fail_times

    async def chat(self, messages, *, temperature, top_p, max_tokens, seed) -> ChatResult:
        from .base import ClientError

        self.calls.append(messages)
        if self._fail_times > 0:
            self._fail_times -= 1
            raise ClientError("mock transient failure")
        text = self.responder(messages, seed)
        chars_in = sum(len(m["content"]) for m in messages)
        return ChatResult(
            text=text,
            tokens_in=chars_in // 4 + 1,
            tokens_out=len(text) // 4 + 1,
            latency_ms=1.0,
        )


def scripted(turns: list[str]) -> Responder:
    """Responder that replays `turns` by counting ASSISTANT turns so far —
    deterministic under retries and confidence turns."""

    def responder(messages: list[dict], seed: int) -> str:
        n_assistant = sum(1 for m in messages if m["role"] == "assistant")
        i = min(n_assistant, len(turns) - 1)
        return turns[i]

    return responder
