"""QA grading (§4.5): SQuAD normalization, token-F1 + EM, max over aliases.

Faithful reimplementation of the official SQuAD/HotpotQA `normalize_answer`
(lowercase → strip punctuation → strip articles → collapse whitespace) and
token-F1. MuSiQue: max over the gold answer plus its aliases. Deterministic,
program-only — no LLM judge (§4.5 rationale).
"""

from __future__ import annotations

import re
import string
from collections import Counter

_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = str.maketrans("", "", string.punctuation)


def normalize_answer(s: str) -> str:
    s = s.lower()
    s = s.translate(_PUNCT)
    s = _ARTICLES.sub(" ", s)
    return " ".join(s.split())


def f1_score(prediction: str, gold: str) -> float:
    pred_toks = normalize_answer(prediction).split()
    gold_toks = normalize_answer(gold).split()
    if not pred_toks or not gold_toks:
        return float(pred_toks == gold_toks)
    common = Counter(pred_toks) & Counter(gold_toks)
    n_same = sum(common.values())
    if n_same == 0:
        return 0.0
    precision = n_same / len(pred_toks)
    recall = n_same / len(gold_toks)
    return 2 * precision * recall / (precision + recall)


def exact_match(prediction: str, gold: str) -> bool:
    return normalize_answer(prediction) == normalize_answer(gold)


def grade(prediction: str | None, golds: list[str]) -> tuple[float, bool]:
    """(max token-F1, max EM) over gold + aliases; unanswered ⇒ (0, False)."""
    if prediction is None or not golds:
        return 0.0, False
    f1 = max(f1_score(prediction, g) for g in golds)
    em = any(exact_match(prediction, g) for g in golds)
    return f1, em
