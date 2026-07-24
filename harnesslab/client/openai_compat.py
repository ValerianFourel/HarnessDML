"""Async OpenAI-compatible chat client (vLLM servers, Blablador). httpx only.

Per-request sampling seed is forwarded (vLLM SamplingParams.seed, §4.6).
Retries with exponential backoff on transport errors and 5xx; terminal
failures raise ClientError (rollout -> finish_reason=api_error).
"""

from __future__ import annotations

import asyncio
import time

import httpx

from .base import ChatResult, ClientError


class OpenAICompatClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "EMPTY",
        timeout_s: float = 180.0,
        max_retries: int = 3,
        chat_template_kwargs: dict | None = None,
    ):
        self.model = model
        self.max_retries = max_retries
        # Per-family template accommodation (constant within a model, like
        # system_role_mode): e.g. {"enable_thinking": false} for Qwen3.x,
        # whose hybrid thinking otherwise floods content past any step cap.
        self.chat_template_kwargs = chat_template_kwargs or {}
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_s,
        )

    async def chat(self, messages, *, temperature, top_p, max_tokens, seed) -> ChatResult:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "seed": seed,
        }
        if self.chat_template_kwargs:
            payload["chat_template_kwargs"] = self.chat_template_kwargs
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            t0 = time.monotonic()
            try:
                resp = await self._http.post("/chat/completions", json=payload)
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"server {resp.status_code}", request=resp.request, response=resp
                    )
                resp.raise_for_status()
                data = resp.json()
                usage = data.get("usage") or {}
                message = data["choices"][0]["message"]
                return ChatResult(
                    text=message.get("content") or "",
                    tokens_in=int(usage.get("prompt_tokens", 0)),
                    tokens_out=int(usage.get("completion_tokens", 0)),
                    latency_ms=(time.monotonic() - t0) * 1000.0,
                    # vLLM renamed reasoning_content -> reasoning (RFC #27755,
                    # OpenAI's gpt-oss guidance); read both for compatibility
                    reasoning_chars=len(
                        message.get("reasoning") or message.get("reasoning_content") or ""
                    ),
                )
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(2.0**attempt)
        raise ClientError(f"chat failed after {self.max_retries + 1} attempts: {last_exc}")

    async def aclose(self) -> None:
        await self._http.aclose()
