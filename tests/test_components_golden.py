"""§8.1 — golden prompts: 32 configs × 3 orderings × 3 templates × 2 families,
exactness via committed hashes + full-text exemplars. Plus padding length
match and the bridge-arm (coupled submission) semantics."""

import hashlib
import json
from pathlib import Path

import pytest

from harnesslab.components import (
    ORDERINGS,
    TEMPLATE_IDS,
    all_cells,
    compose,
    config_id,
)
from harnesslab.components.compose import SUBMISSION, _block_text
from harnesslab.components.padding import TOLERANCE, padded_block

GOLDEN = Path(__file__).parent / "golden"


def test_all_cells_is_the_full_factorial():
    cells = all_cells()
    assert len(cells) == 32
    assert len(set(map(config_id, cells))) == 32
    assert config_id(cells[0]) == "BARE"


def test_576_composed_prompts_match_golden_hashes():
    expected = json.loads((GOLDEN / "prompt_hashes.json").read_text())
    assert len(expected) == 32 * 3 * 3 * 2
    live = {}
    for family in ("qa", "math"):
        for cell in all_cells():
            for oid in ORDERINGS:
                for tid in TEMPLATE_IDS:
                    text = compose(family, cell, ordering_id=oid, template_id=tid).text
                    key = f"{family}|{config_id(cell)}|{oid}|{tid}"
                    live[key] = hashlib.sha256(text.encode()).hexdigest()[:16]
    assert live == expected, "template drift — a frozen prompt changed"


def test_exemplar_full_texts_exact():
    cases = {
        "hotpotqa_BARE_o1_t1.txt": ("qa", frozenset()),
        "hotpotqa_T+SR+R_o1_t1.txt": ("qa", frozenset({"T", "SR", "R"})),
        "hotpotqa_ALL_o1_t1.txt": ("qa", frozenset({"P", "T", "M", "SR", "R"})),
        "gsm8k_T_o1_t1.txt": ("math", frozenset({"T"})),
    }
    for name, (family, cell) in cases.items():
        want = (GOLDEN / "prompts" / name).read_text()
        assert compose(family, cell).text + "\n" == want, name


def test_every_config_gets_universal_submission():
    for family in ("qa", "math"):
        for cell in all_cells():
            assert SUBMISSION in compose(family, cell).text  # §4.2.1 decoupling


def test_ordering_changes_block_order_not_content():
    cell = frozenset({"P", "T", "SR"})
    a = compose("qa", cell, ordering_id="o1")
    b = compose("qa", cell, ordering_id="o2")
    assert a.text != b.text
    assert sorted(a.text.split("\n\n")) == sorted(b.text.split("\n\n"))


def test_bridge_arm_coupled_submission():
    with_t = compose("qa", frozenset({"T"}), coupled_submission=True).text
    assert with_t.count(SUBMISSION) == 1  # inside the T block only
    bare = compose("qa", frozenset(), coupled_submission=True).text
    assert SUBMISSION not in bare  # CCI-style: no T, no way to submit


def test_padding_is_length_matched():
    for comp in ("P", "M", "SR", "R"):
        real = _block_text(comp, "qa", "t1")
        pad = padded_block(real, comp)
        assert abs(len(pad) - len(real)) / len(real) <= TOLERANCE + 0.02
        assert pad != real
    padded = compose("qa", frozenset({"P", "T"}), padding_components={"P"})
    assert "P:padding" in padded.block_hashes


def test_block_hashes_cover_all_rendered_blocks():
    c = compose("qa", frozenset({"P", "T", "M", "SR", "R"}))
    assert set(c.block_hashes) == {"base", "P:t1", "T:t1", "M:t1", "SR:t1", "R:t1", "submission"}


@pytest.mark.parametrize("bad", [("zz", frozenset()), ("qa", frozenset({"X"}))])
def test_compose_rejects_unknowns(bad):
    family, cell = bad
    with pytest.raises(ValueError):
        compose(family, cell)
