"""Length-matched padding pseudo-components (CCI §7.1 control arm, §4.3.3).

For any real component block, `padded_block()` produces meaningless-but-fluent
filler whose character count matches the real block within ±5%, so the padding
arm separates content effects from prompt-length effects. Deterministic.
"""

from __future__ import annotations

_FILLER_SENTENCES = [
    "The following section contains general procedural guidance for this task.",
    "Standard operating practice applies to all portions of the work described here.",
    "Routine considerations should be handled in the customary and usual manner.",
    "General provisions of this notice apply throughout the remainder of the task.",
    "Ordinary care is expected at each stage in accordance with common practice.",
    "The material in this section is provided for completeness of the instructions.",
]

TOLERANCE = 0.05


def padded_block(real_text: str, component_name: str) -> str:
    """Filler block length-matched to `real_text` (±5% characters)."""
    header = f"Section {component_name}: "
    target = len(real_text)
    out = header
    i = 0
    while len(out) < target:
        out += ("" if out is header else " ") + _FILLER_SENTENCES[i % len(_FILLER_SENTENCES)]
        i += 1
    if len(out) > target * (1 + TOLERANCE):
        cut = out[: int(target * (1 + TOLERANCE))]
        out = cut[: cut.rfind(" ")] + "."
    return out
