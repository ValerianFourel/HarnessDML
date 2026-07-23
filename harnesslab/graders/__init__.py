"""Deterministic graders (§4.5) — score ONLY the extracted `Answer:` line."""

from __future__ import annotations

from . import math_sympy, numeric, qa_f1_em  # noqa: F401


def grade_rollout(benchmark: str, answer: str | None, task: dict) -> tuple[float, bool, str]:
    """(y, em, grader_path) for one rollout. Unanswered ⇒ y=0, em=False.

    Gold format per benchmark (tasks jsonl): qa → task['answers'] list
    (gold + aliases); gsm8k → task['gold'] number string; math → task['gold']
    latex-ish string.
    """
    if benchmark in ("hotpotqa", "musique"):
        f1, em = qa_f1_em.grade(answer, task["answers"])
        return f1, em, "qa_f1"
    if benchmark == "gsm8k":
        ok = numeric.grade(answer, task["gold"])
        return float(ok), ok, "numeric"
    if benchmark == "math":
        ok, path = math_sympy.grade(answer, task["gold"])
        return float(ok), ok, path
    raise ValueError(f"unknown benchmark {benchmark!r}")
