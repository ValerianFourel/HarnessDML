"""MATH grading (§4.5): sympy canonicalization + symbolic equivalence, with a
string-match fallback (grader_path logged). Deterministic, program-only.

Pipeline: latex-ish cleanup -> sympify -> simplify(a-b)==0, with a numeric
evalf comparison as the equivalence fallback (sympy simplify can be brittle);
if parsing fails on either side, fall back to normalized string equality and
report grader_path='sympy_string_fallback'.
"""

from __future__ import annotations

import re

import sympy as sp

_BOXED_RE = re.compile(r"\\boxed\s*\{")
_FRAC_RE = re.compile(r"\\[dt]?frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}")
_SQRT_N_RE = re.compile(r"\\sqrt\s*\[([^\]]+)\]\s*\{([^{}]+)\}")
_SQRT_RE = re.compile(r"\\sqrt\s*\{([^{}]+)\}")
_TEXT_RE = re.compile(r"\\text\s*\{[^{}]*\}")


def _strip_boxed(s: str) -> str:
    m = _BOXED_RE.search(s)
    if not m:
        return s
    start = m.end()
    depth = 1
    for i in range(start, len(s)):
        depth += {"{": 1, "}": -1}.get(s[i], 0)
        if depth == 0:
            return s[start:i]
    return s[start:]


def canonicalize(s: str) -> str:
    s = s.strip().strip("$")
    s = _strip_boxed(s)
    s = _TEXT_RE.sub("", s)
    for tok in ("\\left", "\\right", "\\!", "\\,", "\\;", "\\ "):
        s = s.replace(tok, "")
    prev = None
    while prev != s:  # nested fractions resolve inner-first
        prev = s
        s = _FRAC_RE.sub(r"((\1)/(\2))", s)
        s = _SQRT_N_RE.sub(r"((\2)**(1/(\1)))", s)
        s = _SQRT_RE.sub(r"sqrt(\1)", s)
    s = s.replace("\\pi", "pi").replace("\\cdot", "*").replace("\\times", "*")
    s = s.replace("^", "**").replace("{", "(").replace("}", ")")
    s = s.replace("\\", "")
    return s.strip()


def _parse(s: str):
    try:
        return sp.sympify(canonicalize(s), rational=True)
    except Exception:  # noqa: BLE001 — any parse failure routes to fallback
        return None


def _equivalent(a, b) -> bool:
    try:
        if sp.simplify(a - b) == 0:
            return True
    except Exception:  # noqa: BLE001
        pass
    try:  # numeric fallback for expressions simplify() cannot settle
        fa, fb = complex(sp.N(a, 30)), complex(sp.N(b, 30))
        return abs(fa - fb) <= 1e-12 * max(1.0, abs(fa), abs(fb))
    except Exception:  # noqa: BLE001
        return False


def grade(prediction: str | None, gold: str) -> tuple[bool, str]:
    """(exact-match-equivalent, grader_path ∈ {sympy, sympy_string_fallback})."""
    if prediction is None:
        return False, "sympy"
    pa, ga = _parse(prediction), _parse(gold)
    if pa is not None and ga is not None:
        return _equivalent(pa, ga), "sympy"
    same = canonicalize(prediction).replace(" ", "") == canonicalize(gold).replace(" ", "")
    return same, "sympy_string_fallback"
