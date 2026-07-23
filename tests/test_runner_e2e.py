"""End-to-end on the mock backend: schedule → loop → grade → store → resume →
aggregate → panel/cell_metrics/REPORT. Rows must be panel-schema-exact."""

import asyncio
import json

import polars as pl

from harnesslab.agent.runner import run_experiment
from harnesslab.aggregate import aggregate
from harnesslab.client import MockClient
from harnesslab.experiment import from_yaml
from harnesslab.panel import load_panel, panel_columns

EXP_YAML = "tests/fixtures/exp_mock_qa.yaml"


def responder(messages, seed):
    """Deterministic scripted policy over the fixture tasks.

    qa1: correct only on seed 0 (drives c_out variation).
    qa2: correct only after a Search observation (drives the T contrast).
    qa3: always wrong. Tool configs search once before answering.
    """
    if "Rate your confidence" in messages[-1]["content"]:
        return "80"
    all_user = " ".join(m["content"] for m in messages if m["role"] == "user")
    tools_on = "Tools:" in messages[0]["content"]
    if tools_on and "Observation:" not in all_user:
        return "Action: Search[Heidelberg]"  # tool configs always search once
    if "Heidelberg located" in all_user:
        return "Answer: Germany" if seed == 0 else "Answer: France"
    if "river" in all_user:
        return "Answer: Neckar" if "Neckar" in all_user else "Answer: Rhine"
    return "Answer: Unknown"


def _run(tmp_path):
    spec = from_yaml(EXP_YAML)
    client = MockClient(responder)
    summary = asyncio.run(run_experiment(spec, client, tmp_path / "rollouts", run_id="test"))
    return spec, summary


def test_end_to_end_and_resume(tmp_path):
    spec, summary = _run(tmp_path)
    assert summary.total == 2 * 3 * 2 == 12
    assert summary.ran == 12 and summary.already_done == 0

    # resume is a no-op by construction (§7)
    _, again = _run(tmp_path)
    assert again.ran == 0 and again.already_done == 12

    out = aggregate(tmp_path / "rollouts", tmp_path / "results")
    panel = load_panel(out["panel"], covariates=["comp_T", "task_id", "benchmark"])
    assert len(panel) == 12
    assert set(panel.columns) == set(panel_columns())
    assert panel["rollout_key"].n_unique() == 12
    assert panel["answered"].all()

    # the engineered T contrast: qa2 correct with tools, wrong without
    em = {
        (bool(t), task): rows["em"].to_list()
        for (t, task), rows in panel.group_by(["comp_T", "task_id"], maintain_order=True)
    }
    assert em[(True, "qa2")] == [True, True]
    assert em[(False, "qa2")] == [False, False]
    assert sorted(em[(True, "qa1")]) == [False, True]  # seed-dependent

    tool_calls = panel.filter(pl.col("comp_T"))["n_tool_calls"]
    assert tool_calls.min() >= 1
    assert (panel.filter(~pl.col("comp_T"))["n_tool_calls"] == 0).all()

    cells = pl.read_parquet(out["cell_metrics"])
    assert len(cells) == 2
    t_cell = cells.filter(pl.col("config_id") == "T+SR+R").row(0, named=True)
    bare = cells.filter(pl.col("config_id") == "BARE").row(0, named=True)
    assert t_cell["em_mean"] == 0.5 and bare["em_mean"] == 1 / 6
    assert t_cell["k_seeds"] == 2 and t_cell["n_tasks"] == 3
    assert 0.0 <= t_cell["c_out"] <= 1.0

    report = out["report"].read_text()
    assert "T+SR+R" in report and "BARE" in report and "answered" in report

    index = json.loads((tmp_path / "results" / "manifest_index.json").read_text())
    ref = panel["manifest_ref"][0]
    assert ref in index and index[ref]["exp_id"] == spec.exp_id
    assert "T+SR+R" in index[ref]["component_template_hashes"]


def test_budget_refuses_without_pilot_constant(capsys):
    from harnesslab.cli import main

    assert main(["budget", "--exp", EXP_YAML, "--n-tasks", "100"]) == 2
    assert "REFUSED" in capsys.readouterr().err
