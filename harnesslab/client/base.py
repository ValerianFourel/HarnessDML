"""Chat client contract. One interface for vLLM, Blablador, and the mock."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ClientError(RuntimeError):
    """Terminal client failure (after retries) — rollout ends api_error."""


@dataclass(frozen=True)
class ChatResult:
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    # reasoning-channel characters (vLLM `reasoning_content`, e.g. gpt-oss
    # harmony): hidden text is real cost — tokens_out already includes it,
    # this makes it visible in the char accounting too. 0 where absent.
    reasoning_chars: int = 0


class ChatClient(Protocol):
    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float,
        top_p: float,
        max_tokens: int,
        seed: int,
    ) -> ChatResult: ...
