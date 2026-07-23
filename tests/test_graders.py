"""§8.4 — grader parity fixtures: SQuAD normalization table, numeric
normalization table, sympy equivalent/known-distinct pairs."""

import pytest

from harnesslab.graders import grade_rollout, math_sympy, numeric, qa_f1_em


# ── QA (SQuAD semantics) ─────────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("The  Empire State Building!", "empire state building"),
    ("An apple; a day.", "apple day"),
    ("Barack   Obama", "barack obama"),
    ("'42'", "42"),
])
def test_squad_normalization(raw, expected):
    assert qa_f1_em.normalize_answer(raw) == expected


def test_f1_partial_overlap():
    assert qa_f1_em.f1_score("Barack Obama", "Obama") == pytest.approx(2 / 3)
    assert qa_f1_em.f1_score("exact match", "exact match") == 1.0
    assert qa_f1_em.f1_score("nothing", "everything") == 0.0


def test_em_and_alias_max():
    f1, em = qa_f1_em.grade("the Neckar", ["Neckar", "Neckar river"])
    assert em is True and f1 == 1.0
    f1, em = qa_f1_em.grade("Neckar river", ["Neckar"])
    assert em is False and f1 == pytest.approx(2 / 3)


def test_unanswered_is_zero():
    assert qa_f1_em.grade(None, ["x"]) == (0.0, False)


# ── GSM8K numeric ────────────────────────────────────────────────────────────
def test_gold_extraction():
    assert numeric.gold_from_gsm8k("reasoning...\n#### 72") == "72"
    with pytest.raises(ValueError):
        numeric.gold_from_gsm8k("no gold here")


@pytest.mark.parametrize("pred,gold,ok", [
    ("72", "72", True),
    ("72.0", "72", True),
    ("$1,234.00", "1234", True),
    ("The answer is 72 dollars", "72", True),
    ("50%", "50", True),
    ("-3", "-3", True),
    ("72.5", "72", False),
    ("no number at all", "72", False),
])
def test_numeric_table(pred, gold, ok):
    assert numeric.grade(pred, gold) is ok


# ── MATH sympy ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("a,b", [
    ("\\frac{1}{2}", "0.5"),
    ("\\boxed{\\frac{\\sqrt{2}}{2}}", "1/\\sqrt{2}"),
    ("x+1", "1+x"),
    ("2^3", "8"),
    ("\\frac{3}{4}", "0.75"),
    ("\\left(\\frac{1}{3}\\right)", "1/3"),
])
def test_sympy_equivalent_pairs(a, b):
    ok, path = math_sympy.grade(a, b)
    assert ok is True and path == "sympy"


@pytest.mark.parametrize("a,b", [
    ("\\frac{1}{2}", "\\frac{1}{3}"),
    ("x+1", "x-1"),
    ("\\sqrt{2}", "2"),
])
def test_sympy_known_distinct_pairs(a, b):
    ok, path = math_sympy.grade(a, b)
    assert ok is False and path == "sympy"


def test_string_fallback_path_is_flagged():
    ok, path = math_sympy.grade("\\weird{unparseable", "\\weird{unparseable")
    assert ok is True and path == "sympy_string_fallback"


# ── dispatch ─────────────────────────────────────────────────────────────────
def test_grade_rollout_dispatch():
    assert grade_rollout("hotpotqa", "Germany", {"answers": ["Germany"]}) == (1.0, True, "qa_f1")
    y, em, path = grade_rollout("gsm8k", "14", {"gold": "14"})
    assert (y, em, path) == (1.0, True, "numeric")
    y, em, path = grade_rollout("math", "\\frac{1}{2}", {"gold": "0.5"})
    assert (y, em, path) == (1.0, True, "sympy")
    assert grade_rollout("hotpotqa", None, {"answers": ["x"]})[0] == 0.0
    with pytest.raises(ValueError):
        grade_rollout("swebench", "x", {})
