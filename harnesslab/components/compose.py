"""compose(): the single system-prompt assembler for every cell (§4.1–4.2).

Layout (exact, golden-tested):

    {base header for the benchmark family}
    <blank line>
    {component blocks that are ON, in the ordering_id order, blank-line separated}
    <blank line>
    {universal submission instruction}

Deviations honored here:
- §4.2.1 submission decoupled from T: every config gets the `Answer:` line
  instruction. Bridge arm (`coupled_submission=True`) reproduces CCI coupling:
  the submission text lives INSIDE the T block, and configs without T get no
  submission instruction at all.
- §4.3.3 padding: components named in `padding` render as length-matched
  filler instead of their real text.

Content hashes of every rendered block are returned for manifests (freeze).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from . import memory, padding, planning, reflection, structured_reasoning, tool_use

COMPONENTS = ("P", "T", "M", "SR", "R")

ORDERINGS = {
    "o1": ("P", "T", "M", "SR", "R"),
    "o2": ("R", "SR", "M", "T", "P"),
    "o3": ("T", "M", "P", "R", "SR"),
}

TEMPLATE_IDS = ("t1", "t2", "t3")

BASE_HEADER = {
    "qa": (
        "You are solving a question-answering task. Work step by step and "
        "answer the question exactly and concisely."
    ),
    "math": (
        "You are solving a math problem. Work step by step and compute the "
        "final result carefully."
    ),
}

SUBMISSION = (
    "When you know the final answer, finish with a single line in exactly "
    "this form:\nAnswer: <your final answer>"
)

_PROMPT_ONLY = {
    "P": planning.TEMPLATES,
    "M": memory.TEMPLATES,
    "SR": structured_reasoning.TEMPLATES,
    "R": reflection.TEMPLATES,
}


@dataclass(frozen=True)
class Composed:
    text: str
    block_hashes: dict[str, str]  # block name -> sha256[:12] of rendered text


def config_id(components: frozenset[str] | set[str]) -> str:
    """Canonical cell encoding: 'BARE' or e.g. 'P+T+SR' in P,T,M,SR,R order."""
    on = [c for c in COMPONENTS if c in components]
    return "+".join(on) if on else "BARE"


def _block_text(comp: str, family: str, template_id: str) -> str:
    if comp == "T":
        return tool_use.TEMPLATES[family][template_id]
    return _PROMPT_ONLY[comp][template_id]


def compose(
    family: str,
    components: frozenset[str] | set[str],
    ordering_id: str = "o1",
    template_id: str = "t1",
    coupled_submission: bool = False,
    padding_components: frozenset[str] | set[str] = frozenset(),
) -> Composed:
    if family not in BASE_HEADER:
        raise ValueError(f"unknown benchmark family {family!r}")
    unknown = set(components) - set(COMPONENTS)
    if unknown:
        raise ValueError(f"unknown components {sorted(unknown)}")
    if ordering_id not in ORDERINGS:
        raise ValueError(f"unknown ordering_id {ordering_id!r}")
    if template_id not in TEMPLATE_IDS:
        raise ValueError(f"unknown template_id {template_id!r}")

    hashes: dict[str, str] = {}

    def h(name: str, text: str) -> str:
        hashes[name] = hashlib.sha256(text.encode()).hexdigest()[:12]
        return text

    parts = [h("base", BASE_HEADER[family])]
    for comp in ORDERINGS[ordering_id]:
        if comp not in components:
            continue
        text = _block_text(comp, family, template_id)
        if comp in padding_components:
            text = padding.padded_block(text, comp)
            name = f"{comp}:padding"
        else:
            name = f"{comp}:{template_id}"
        if comp == "T" and coupled_submission:
            text = text + "\n" + SUBMISSION
        parts.append(h(name, text))

    if coupled_submission:
        pass  # bridge arm: submission only exists inside T (or not at all)
    else:
        parts.append(h("submission", SUBMISSION))

    return Composed(text="\n\n".join(parts), block_hashes=hashes)


def all_cells() -> list[frozenset[str]]:
    """The 32 configurations, in canonical bitmask order (BARE first)."""
    cells = []
    for mask in range(32):
        cells.append(frozenset(c for i, c in enumerate(COMPONENTS) if mask >> i & 1))
    return sorted(cells, key=lambda s: (len(s), config_id(s)))
