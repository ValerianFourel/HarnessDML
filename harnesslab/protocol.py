"""The ONE textual protocol shared by composer, agent loop, and graders (§4.2.2).

Strict, line-anchored grammar. No native function calling anywhere — a single
regex family parses every model in the study identically.
"""

from __future__ import annotations

import re

# Exactly one action per assistant message, on its own line.
ACTION_RE = re.compile(r"^Action:\s*(Search|Lookup|Calculate)\[(.*)\]\s*$", re.MULTILINE)

# Final submission line (universal across configs, §4.2.1).
ANSWER_RE = re.compile(r"^Answer:\s*(.*\S)\s*$", re.MULTILINE)

# Confidence elicitation reply: ONLY a number (§5).
CONFIDENCE_RE = re.compile(r"^\s*(\d{1,3})(?:\.\d+)?\s*$")

ACTION_CODES = {"Search": "S", "Lookup": "L", "Calculate": "C"}
ANSWER_CODE = "A"


def parse_action(text: str) -> tuple[str, str] | None:
    """First grammatical action line -> (verb, argument), else None."""
    m = ACTION_RE.search(text)
    return (m.group(1), m.group(2).strip()) if m else None


def parse_answer(text: str) -> str | None:
    """LAST `Answer:` line (models sometimes restate); None if absent."""
    found = ANSWER_RE.findall(text)
    return found[-1].strip() if found else None


def looks_like_action_attempt(text: str) -> bool:
    """Distinguishes malformed-action failures (-> parse_loop) from
    no-action-no-answer prose (-> no_answer)."""
    return "Action:" in text


def parse_confidence(text: str) -> float | None:
    m = CONFIDENCE_RE.match(text or "")
    if not m:
        return None
    v = float(m.group(1))
    return v if 0 <= v <= 100 else None
