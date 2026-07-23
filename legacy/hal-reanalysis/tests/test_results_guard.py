"""Guardrail 4: the results-contract size/path guard used before HPC pushes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_results_size import MAX_BYTES, violations  # noqa: E402


def test_results_and_schema_paths_pass():
    assert violations([
        ("results/estimates/reasoning_v0/ladder_run1.csv", 10_000),
        ("results/manifests/20260723T000000Z-abcd1234.json", 2_000),
        ("schema/SCHEMA.md", 50_000),
    ]) == []


def test_code_paths_are_blocked():
    problems = violations([("src/halcausal/guards.py", 10)])
    assert len(problems) == 1 and "outside" in problems[0]


def test_data_paths_are_blocked():
    assert violations([("data/encrypted/taubench_airline/run.json", 5)])


def test_oversize_file_blocked_even_inside_results():
    problems = violations([("results/panel/huge.parquet", MAX_BYTES + 1)])
    assert len(problems) == 1 and "25 MB" in problems[0]


def test_oversize_outside_results_reports_both():
    assert len(violations([("data/big.bin", MAX_BYTES + 1)])) == 2
