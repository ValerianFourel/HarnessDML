"""GSM8K grading (§4.5): numeric equality vs the `#### n` gold after
normalization (commas, $, %, unit words, trailing .0). Deterministic."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_GOLD_RE = re.compile(r"####\s*(.+?)\s*$", re.MULTILINE)
_NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def gold_from_gsm8k(answer_field: str) -> str:
    """Extract the gold number from a GSM8K answer string ('... #### 72')."""
    m = _GOLD_RE.search(answer_field)
    if not m:
        raise ValueError("no '#### n' gold in answer field")
    return m.group(1)


def parse_number(s: str) -> Decimal | None:
    """First numeric token after stripping $, %, commas; None if absent."""
    if s is None:
        return None
    cleaned = s.replace("$", " ").replace("%", " ")
    m = _NUMBER_RE.search(cleaned)
    if not m:
        return None
    try:
        return Decimal(m.group(0).replace(",", ""))
    except InvalidOperation:
        return None


def grade(prediction: str | None, gold: str) -> bool:
    """Exact numeric equality (Decimal — so 72 == 72.0, 1,234 == 1234)."""
    if prediction is None:
        return False
    p, g = parse_number(prediction), parse_number(gold)
    return p is not None and g is not None and p == g
