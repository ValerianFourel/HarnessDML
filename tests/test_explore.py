"""Exploration sweep: per-file summaries, aggregation, redaction, clipping."""

import json

from halcausal import explore


def _write(tmp_path, name, doc):
    p = tmp_path / name
    p.write_text(json.dumps(doc))
    return p


def test_summarize_run_file(tmp_path):
    doc = {
        "config": {
            "model_name": "gpt-5",
            "openai_api_key": "sk-live-oops",
            "prompt_template": "x" * 500,
            "agent_args": {"reasoning_effort": "high"},
        },
        "results": {"accuracy": 0.42},
        "raw_logging_results": [{"a": 1}, {"a": 2}, {"a": 3}],
        "raw_eval_results": {f"task_{i}": {} for i in range(300)},
    }
    rec = explore.summarize_run_file(_write(tmp_path, "taubench_airline_x_UPLOAD.json", doc))

    assert rec["benchmark_guess"] == "taubench_airline"
    assert rec["top_level"]["config"] == {"type": "dict", "n_keys": 4}
    assert rec["small_blocks"]["config"]["openai_api_key"] == "«redacted»"
    assert rec["small_blocks"]["config"]["prompt_template"].endswith("…")
    assert len(rec["small_blocks"]["config"]["prompt_template"]) == 201
    assert rec["small_blocks"]["config"]["agent_args"] == {"reasoning_effort": "high"}
    assert rec["small_blocks"]["results"] == {"accuracy": 0.42}
    assert rec["collection_sizes"] == {"raw_logging_results": 3, "raw_eval_results": 300}


def test_aggregate(tmp_path):
    docs = [
        {"config": {"model_name": "gpt-5", "agent_args": {"reasoning_effort": "high"}},
         "raw_logging_results": [1, 2, 3]},
        {"config": {"model_name": "o3"},
         "raw_logging_results": [1]},
    ]
    records = [
        explore.summarize_run_file(_write(tmp_path, f"taubench_airline_{i}_UPLOAD.json", d))
        for i, d in enumerate(docs)
    ]
    agg = explore.aggregate(records)

    assert agg["n_files"] == 2
    assert agg["top_level_key_presence"]["config"] == "2/2"
    assert agg["field_value_counts"]["config.model_name"] == {"gpt-5": 1, "o3": 1}
    assert agg["field_value_counts"]["config.agent_args.reasoning_effort"] == {"high": 1}
    assert agg["collection_sizes"]["raw_logging_results"] == {
        "min": 1, "median": 2, "max": 3, "sum": 4,
    }


def test_non_dict_root_does_not_crash(tmp_path):
    rec = explore.summarize_run_file(_write(tmp_path, "weird_UPLOAD.json", [1, 2]))
    assert rec["top_level"]["<root>"] == {"type": "list"}
