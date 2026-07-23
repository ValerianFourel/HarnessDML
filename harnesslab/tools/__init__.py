"""Hermetic tools (§4.2.3) and the per-family toolbox used by the agent loop."""

from __future__ import annotations

from .calculator import calculate
from .docstore import DocStore


class ToolBox:
    """Dispatches parsed actions to the benchmark family's tools.

    QA: Search/Lookup over the task's DocStore. Math: Calculate only.
    Unknown verbs for the family fail closed with an observation string
    (the loop still counts the turn; grammar-level failures are handled
    earlier by the parser).
    """

    def __init__(self, family: str, docstore: DocStore | None = None):
        if family not in ("qa", "math"):
            raise ValueError(f"unknown family {family!r}")
        if family == "qa" and docstore is None:
            raise ValueError("qa toolbox requires a DocStore")
        self.family = family
        self.docstore = docstore

    def allowed(self, verb: str) -> bool:
        return verb in (("Search", "Lookup") if self.family == "qa" else ("Calculate",))

    def dispatch(self, verb: str, arg: str) -> str:
        if not self.allowed(verb):
            return f"Unknown action {verb} for this task."
        if verb == "Search":
            return self.docstore.search(arg)
        if verb == "Lookup":
            return self.docstore.lookup(arg)
        return calculate(arg)
