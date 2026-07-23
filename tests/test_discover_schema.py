"""Phase-1 walker: path collapsing, type unions, presence, suggestions."""

import json

import pytest
import yaml

from halcausal.etl import discover_schema


@pytest.fixture()
def trace_dir(tmp_path):
    doc1 = {
        "config": {"model": "gpt-5", "agent_name": "tau_agent", "reasoning_effort": "high"},
        "results": {"accuracy": 0.5, "total_cost": 1.23},
        "raw_logging_results": [
            {"usage": {"prompt_tokens": 10, "completion_tokens": 5}, "weave_task_id": "a1b2c3d4e5f60718"},
            {"usage": {"prompt_tokens": 20, "completion_tokens": 7}, "weave_task_id": "ffeeddccbbaa9988"},
        ],
        "raw_eval_results": {f"task_{i:04d}": {"passed": i % 2 == 0} for i in range(15)},
    }
    doc2 = {
        "config": {"model": "o3", "agent_name": "tau_agent"},  # no reasoning_effort
        "results": {"accuracy": "0.7", "total_cost": 2.5},  # str vs float union
        "raw_logging_results": [],
        "raw_eval_results": {f"task_{i:04d}": {"passed": False} for i in range(15)},
    }
    for i, doc in enumerate((doc1, doc2)):
        (tmp_path / f"run{i}.json").write_text(json.dumps(doc))
    return tmp_path


def test_report_and_artifacts(trace_dir):
    md = discover_schema(trace_dir, out_md=trace_dir / "schema" / "SCHEMA.md", n_files=10)
    text = md.read_text()

    assert "STATUS: UNREVIEWED" in text
    assert "`$.config.model`" in text
    # 15 id-like keys -> collapsed, per-id keys never appear as named paths
    assert "`$.raw_eval_results.{*}.passed`" in text and "task_0003" not in text
    # array elements walked
    assert "`$.raw_logging_results[].usage.prompt_tokens`" in text
    # type union across files
    assert "float|str" in text
    # presence: reasoning_effort in 1 of 2 files
    assert "| `$.config.reasoning_effort` | str | 1 | 50% | 50% |" in text

    stats = json.loads((md.parent / "paths.json").read_text())
    assert stats["$.config.reasoning_effort"]["files"] == 1
    assert stats["$.raw_eval_results"]["collapsed_key_cardinality"] == [15, 15]

    sugg = yaml.safe_load((md.parent / "field_mapping.suggested.yaml").read_text())
    assert any(c["path"] == "$.config.reasoning_effort" for c in sugg["reasoning_effort"])
    assert any(c["path"] == "$.results.accuracy" for c in sugg["success"])
    assert any(c["path"] == "$.config.model" for c in sugg["model"])


def test_all_files_skipped_raises(trace_dir):
    with pytest.raises(RuntimeError, match="walked 0"):
        discover_schema(trace_dir, out_md=trace_dir / "s" / "SCHEMA.md", n_files=10, max_file_gb=1e-9)


def test_empty_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="no decrypted"):
        discover_schema(tmp_path)
