"""Regenerate the golden prompt corpus (§8.1). Run ONLY on a deliberate,
reviewed template change: goldens define the freeze; drift fails tests.

    uv run python scripts/regen_goldens.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from harnesslab.components import ORDERINGS, TEMPLATE_IDS, all_cells, compose, config_id

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "tests" / "golden"

EXEMPLARS = [
    ("qa", frozenset(), "o1", "t1", "hotpotqa_BARE_o1_t1.txt"),
    ("qa", frozenset({"T", "SR", "R"}), "o1", "t1", "hotpotqa_T+SR+R_o1_t1.txt"),
    ("qa", frozenset({"P", "T", "M", "SR", "R"}), "o1", "t1", "hotpotqa_ALL_o1_t1.txt"),
    ("math", frozenset({"T"}), "o1", "t1", "gsm8k_T_o1_t1.txt"),
]


def main() -> None:
    hashes: dict[str, str] = {}
    for family in ("qa", "math"):
        for cell in all_cells():
            for oid in ORDERINGS:
                for tid in TEMPLATE_IDS:
                    text = compose(family, cell, ordering_id=oid, template_id=tid).text
                    key = f"{family}|{config_id(cell)}|{oid}|{tid}"
                    hashes[key] = hashlib.sha256(text.encode()).hexdigest()[:16]

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    (GOLDEN_DIR / "prompt_hashes.json").write_text(
        json.dumps(dict(sorted(hashes.items())), indent=1)
    )

    exemplar_dir = GOLDEN_DIR / "prompts"
    exemplar_dir.mkdir(exist_ok=True)
    for family, cell, oid, tid, name in EXEMPLARS:
        text = compose(family, cell, ordering_id=oid, template_id=tid).text
        (exemplar_dir / name).write_text(text + "\n")

    print(f"wrote {len(hashes)} hashes + {len(EXEMPLARS)} exemplars to {GOLDEN_DIR}")


if __name__ == "__main__":
    main()
