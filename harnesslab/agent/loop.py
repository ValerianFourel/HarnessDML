"""The fixed ReAct-style agent loop (§3 — the Claw "base").

Identical for every configuration: components change ONLY the system prompt
(and whether a toolbox exists, via T). Protocol per §4.2.2: one action per
message, single retry on parse failure (event-logged), universal `Answer:`
submission line, confidence elicitation turn after the answer (§5).

finish_reason semantics (panel enum):
- answered:   an `Answer:` line was parsed (Answer wins if both appear).
- parse_loop: two consecutive failures where a malformed/disallowed ACTION
              attempt was involved.
- no_answer:  two consecutive failures of pure prose (no action attempt, no
              answer) — the model stopped talking without answering.
- step_cap:   turn budget exhausted while still acting validly.
- timeout:    hard wall-clock limit hit before the next model call.
- api_error:  client failed terminally (after its own retries).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..client.base import ChatClient, ClientError
from ..protocol import (
    ACTION_CODES,
    ANSWER_CODE,
    looks_like_action_attempt,
    parse_action,
    parse_answer,
    parse_confidence,
)
from ..tools import ToolBox

RETRY_NUDGE = (
    "Your last message was not valid. Reply with exactly one line "
    "'Action: Tool[argument]' using an available tool, or finish with a "
    "single line 'Answer: <your final answer>'."
)

CONFIDENCE_PROMPT = (
    "Rate your confidence that your final answer is correct on a scale from "
    "0 to 100. Respond with ONLY a number."
)


@dataclass
class RolloutTrace:
    answer: str | None = None
    finish_reason: str = "no_answer"
    n_turns: int = 0
    n_tool_calls: int = 0
    n_parse_failures: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    chars_in: int = 0
    chars_out: int = 0
    chars_out_reasoning: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    action_seq: list[str] = field(default_factory=list)
    confidence: float | None = None
    confidence_source: str | None = None
    wall_s: float = 0.0

    @property
    def answered(self) -> bool:
        return self.finish_reason == "answered"


def build_messages(system_text: str, question: str, system_role_mode: str) -> list[dict]:
    if system_role_mode == "native":
        return [
            {"role": "system", "content": system_text},
            {"role": "user", "content": question},
        ]
    if system_role_mode == "prepended":  # §4.2.4 no-system-role fallback
        return [{"role": "user", "content": system_text + "\n\n" + question}]
    raise ValueError(f"unknown system_role_mode {system_role_mode!r}")


async def run_rollout(
    client: ChatClient,
    system_text: str,
    question: str,
    toolbox: ToolBox | None,
    *,
    step_cap: int,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    seed: int,
    system_role_mode: str = "native",
    timeout_s: float = 600.0,
    elicit_confidence: bool = True,
) -> RolloutTrace:
    t0 = time.monotonic()
    tr = RolloutTrace()
    messages = build_messages(system_text, question, system_role_mode)
    consecutive_failures = 0
    failure_saw_action_attempt = False

    async def call() -> str | None:
        """One model call; accounts usage. None => terminal client error."""
        tr.chars_in += sum(len(m["content"]) for m in messages)
        try:
            res = await client.chat(
                messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_new_tokens,
                seed=seed,
            )
        except ClientError:
            return None
        tr.tokens_in += res.tokens_in
        tr.tokens_out += res.tokens_out
        tr.chars_out += len(res.text)
        tr.chars_out_reasoning += res.reasoning_chars
        tr.latencies_ms.append(res.latency_ms)
        return res.text

    for _ in range(step_cap):
        if time.monotonic() - t0 > timeout_s:
            tr.finish_reason = "timeout"
            break
        text = await call()
        if text is None:
            tr.finish_reason = "api_error"
            break
        tr.n_turns += 1
        messages.append({"role": "assistant", "content": text})

        answer = parse_answer(text)
        if answer is not None:  # Answer wins even if an action also appears
            tr.answer = answer
            tr.finish_reason = "answered"
            tr.action_seq.append(ANSWER_CODE)
            break

        action = parse_action(text)
        if action is not None and toolbox is not None and toolbox.allowed(action[0]):
            verb, arg = action
            observation = toolbox.dispatch(verb, arg)
            tr.n_tool_calls += 1
            tr.action_seq.append(ACTION_CODES[verb])
            messages.append({"role": "user", "content": f"Observation: {observation}"})
            consecutive_failures = 0
            failure_saw_action_attempt = False
            continue

        # failure path: malformed action, disallowed verb, tool-less action,
        # or pure prose without an answer — single retry with a fixed nudge
        tr.n_parse_failures += 1
        attempted = action is not None or looks_like_action_attempt(text)
        failure_saw_action_attempt = failure_saw_action_attempt or attempted
        consecutive_failures += 1
        if consecutive_failures >= 2:
            tr.finish_reason = "parse_loop" if failure_saw_action_attempt else "no_answer"
            break
        messages.append({"role": "user", "content": RETRY_NUDGE})
    else:
        tr.finish_reason = "step_cap"

    if tr.answered and elicit_confidence:
        messages.append({"role": "user", "content": CONFIDENCE_PROMPT})
        text = await call()
        if text is not None:
            tr.n_turns += 1
        tr.confidence = parse_confidence(text) if text is not None else None
        tr.confidence_source = "elicited" if tr.confidence is not None else "fallback"

    tr.wall_s = time.monotonic() - t0
    return tr
