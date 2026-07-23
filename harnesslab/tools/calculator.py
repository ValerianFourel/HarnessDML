"""Sandboxed Calculate[e] for the math benchmarks (§4.2.3). asteval, no eval.

Whitelisted arithmetic only; imports, attribute access, names outside the
whitelist, and statements all fail closed with an error observation string.
"""

from __future__ import annotations

import math
import re

from asteval import Interpreter

_ATTR_RE = re.compile(r"\.\s*[A-Za-z_]")

_ALLOWED_SYMBOLS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
    "min": min,
    "max": max,
}

_MAX_EXPR_LEN = 400


def _fresh_interpreter() -> Interpreter:
    aeval = Interpreter(
        minimal=True,
        use_numpy=False,
        no_ifexp=True,
        no_listcomp=True,
        no_augassign=True,
        no_assert=True,
        no_delete=True,
        no_raise=True,
        no_print=True,
    )
    aeval.symtable.clear()
    aeval.symtable.update(_ALLOWED_SYMBOLS)
    return aeval


def calculate(expression: str) -> str:
    """Evaluate; ALWAYS returns an observation string (errors fail closed)."""
    expr = expression.strip()
    if not expr:
        return "Calculator error: empty expression."
    if len(expr) > _MAX_EXPR_LEN:
        return "Calculator error: expression too long."
    # fail closed on dunder tokens and attribute access (`.x`); decimals like
    # 3.5 are fine because a digit, not a letter/underscore, follows the dot
    if "__" in expr or _ATTR_RE.search(expr):
        return "Calculator error: forbidden token."
    aeval = _fresh_interpreter()
    try:
        value = aeval.eval(expr, show_errors=False, raise_errors=True)
    except Exception as exc:  # noqa: BLE001 — fail closed with reason
        return f"Calculator error: {type(exc).__name__}: {exc}"
    if value is None:
        return "Calculator error: expression produced no value."
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
