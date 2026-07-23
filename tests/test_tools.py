"""§8.3 — docstore determinism + ReAct semantics; calculator sandbox."""

from harnesslab.tools import DocStore, ToolBox
from harnesslab.tools.calculator import calculate

PARAS = [
    ("Heidelberg", "Heidelberg is a city in Germany. It lies on the Neckar river. "
                   "The Neckar flows into the Rhine."),
    ("Lyon", "Lyon is a city in France."),
]


def test_search_exact_and_case_insensitive():
    ds = DocStore(PARAS)
    assert ds.search("Heidelberg").startswith("Heidelberg is a city")
    assert ds.search("heidelberg").startswith("Heidelberg is a city")


def test_search_miss_lists_similar_titles():
    ds = DocStore(PARAS)
    out = ds.search("Paris")
    assert out.startswith("Could not find [Paris]") and "Heidelberg" in out


def test_lookup_cycles_and_exhausts():
    ds = DocStore(PARAS)
    ds.search("Heidelberg")
    first = ds.lookup("Neckar")
    second = ds.lookup("Neckar")
    assert first.startswith("(Result 1/2)") and "Neckar" in first
    assert second.startswith("(Result 2/2)")
    assert ds.lookup("Neckar") == "No more results."


def test_lookup_requires_search_first():
    assert DocStore(PARAS).lookup("x") == "No paragraph selected. Use Search first."


def test_docstore_deterministic():
    a, b = DocStore(PARAS), DocStore(PARAS)
    ops = [("search", "Heidelberg"), ("lookup", "Neckar"), ("lookup", "Neckar"),
           ("search", "nope"), ("lookup", "France")]
    out_a = [getattr(a, f)(arg) for f, arg in ops]
    out_b = [getattr(b, f)(arg) for f, arg in ops]
    assert out_a == out_b


def test_calculator_arithmetic():
    assert calculate("1+2*3") == "7"
    assert calculate("2**10") == "1024"
    assert calculate("sqrt(16)") == "4"
    assert calculate("(1/2)+0.5") == "1"
    assert calculate("-3 + 1") == "-2"


def test_calculator_sandbox_rejects():
    assert calculate("import os").startswith("Calculator error")
    assert calculate("__import__('os')").startswith("Calculator error")
    assert calculate("().__class__").startswith("Calculator error")
    assert calculate("(1).bit_length()").startswith("Calculator error")
    assert calculate("open('/etc/passwd')").startswith("Calculator error")
    assert calculate("x + 1").startswith("Calculator error")
    assert calculate("").startswith("Calculator error")


def test_toolbox_family_gating():
    qa = ToolBox("qa", DocStore(PARAS))
    math = ToolBox("math")
    assert qa.allowed("Search") and not qa.allowed("Calculate")
    assert math.allowed("Calculate") and not math.allowed("Search")
    assert math.dispatch("Calculate", "6*7") == "42"
    assert qa.dispatch("Calculate", "1") == "Unknown action Calculate for this task."
