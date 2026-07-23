"""Hermetic ReAct-style docstore over a task's shipped paragraphs (§4.2.3).

HotpotQA distractor: the 10 shipped paragraphs; MuSiQue: its ~20. Search
returns the best-title-matching paragraph; Lookup steps through sentences of
the most recently searched paragraph containing a keyword. Fully deterministic,
zero network.
"""

from __future__ import annotations

import re
import string

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PUNCT = str.maketrans("", "", string.punctuation)


def _norm(s: str) -> str:
    return " ".join(s.lower().translate(_PUNCT).split())


class DocStore:
    def __init__(self, paragraphs: list[tuple[str, str]]):
        """paragraphs: (title, text), order-preserving."""
        self.paragraphs = list(paragraphs)
        self._by_norm_title = {_norm(t): (t, x) for t, x in self.paragraphs}
        self._current: str | None = None  # text of last successful Search
        self._lookup_kw: str | None = None
        self._lookup_idx = 0

    # ── Search[q] ────────────────────────────────────────────────────────────
    def search(self, query: str) -> str:
        q = _norm(query)
        hit = self._by_norm_title.get(q)
        if hit is None:
            # unique containment fallback (either direction), else miss
            contains = [
                (t, x) for t, x in self.paragraphs
                if q and (q in _norm(t) or _norm(t) in q)
            ]
            if len(contains) == 1:
                hit = contains[0]
        if hit is None:
            similar = self._similar_titles(q)
            return f"Could not find [{query.strip()}]. Similar: {similar}."
        title, text = hit
        self._current = text
        self._lookup_kw, self._lookup_idx = None, 0
        return text

    def _similar_titles(self, q: str, k: int = 5) -> list[str]:
        qtok = set(q.split())

        def overlap(title: str) -> int:
            return len(qtok & set(_norm(title).split()))

        ranked = sorted(self.paragraphs, key=lambda p: (-overlap(p[0]), p[0]))
        return [t for t, _ in ranked[:k]]

    # ── Lookup[k] ────────────────────────────────────────────────────────────
    def lookup(self, keyword: str) -> str:
        if self._current is None:
            return "No paragraph selected. Use Search first."
        kw = keyword.strip().lower()
        if kw != self._lookup_kw:
            self._lookup_kw, self._lookup_idx = kw, 0
        sentences = [s for s in _SENT_SPLIT.split(self._current) if kw in s.lower()]
        if not sentences:
            return f"No sentence containing [{keyword.strip()}] in the current paragraph."
        if self._lookup_idx >= len(sentences):
            return "No more results."
        i = self._lookup_idx
        self._lookup_idx += 1
        return f"(Result {i + 1}/{len(sentences)}) {sentences[i]}"
