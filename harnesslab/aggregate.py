"""Aggregate: rollouts.jsonl → panel.parquet + cell_metrics.parquet +
manifest_index.json + REPORT.md (§5 deliverables). Offline-safe, login-node
committed. Fails loudly if any record deviates from the panel schema."""

from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

from .metrics import calibration, consistency
from .panel import validate_record
from .store import RolloutStore

CELL_KEY = ("exp_id", "model_id", "benchmark", "band", "config_id",
            "ordering_id", "template_id", "temp")

_DTYPES = {
    "seed": pl.Int64, "step_cap": pl.Int64, "max_new_tokens_step": pl.Int64,
    "n_turns": pl.Int64, "n_tool_calls": pl.Int64, "n_parse_failures": pl.Int64,
    "tokens_in": pl.Int64, "tokens_out": pl.Int64,
    "chars_in": pl.Int64, "chars_out": pl.Int64, "chars_out_reasoning": pl.Int64,
    "model_scale_b": pl.Float64, "temp": pl.Float64, "top_p": pl.Float64,
    "task_difficulty_calib": pl.Float64, "y": pl.Float64, "confidence": pl.Float64,
    "server_uptime_s": pl.Float64, "wall_s": pl.Float64, "gpu_seconds": pl.Float64,
    "latency_ms_mean": pl.Float64,
    "comp_P": pl.Boolean, "comp_T": pl.Boolean, "comp_M": pl.Boolean,
    "comp_SR": pl.Boolean, "comp_R": pl.Boolean, "em": pl.Boolean,
    "answered": pl.Boolean,
}


def _mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def cell_metrics_row(rows: list[dict]) -> dict:
    by_task: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(r)

    correct = {t: [bool(r["em"]) for r in rs] for t, rs in by_task.items()}
    seqs = {t: [r["action_seq"].split(">") if r["action_seq"] else [] for r in rs]
            for t, rs in by_task.items()}
    resources = {
        res: {t: [float(r[res]) for r in rs] for t, rs in by_task.items()}
        for res in ("tokens_out", "wall_s", "n_tool_calls")
    }
    success_rows = [r for r in rows if r["em"]]
    by_task_success: dict[str, list[dict]] = defaultdict(list)
    for r in success_rows:
        by_task_success[r["task_id"]].append(r)
    resources_cond = {
        res: {t: [float(r[res]) for r in rs] for t, rs in by_task_success.items()}
        for res in ("tokens_out", "wall_s", "n_tool_calls")
    }

    elicited = [r for r in rows
                if r["confidence_source"] == "elicited" and r["confidence"] is not None]
    conf01 = [r["confidence"] / 100.0 for r in elicited]
    corr = [bool(r["em"]) for r in elicited]

    k_values = {len(v) for v in correct.values()}
    out = {k: rows[0][k] for k in CELL_KEY}
    out.update({
        "n_rollouts": len(rows),
        "n_tasks": len(by_task),
        "k_seeds": max(k_values) if k_values else 0,
        "y_mean": _mean(r["y"] for r in rows),
        "em_mean": _mean(float(r["em"]) for r in rows),
        "answered_rate": _mean(float(r["answered"]) for r in rows),
        "pass_at_k": consistency.pass_at_k(correct),
        "pass_all_k": consistency.pass_all_k(correct),
        "c_out": consistency.c_out(correct),
        "c_traj_d": consistency.c_traj_d(seqs),
        "c_traj_s": consistency.c_traj_s(seqs),
        "c_res_uncond": consistency.c_res(resources),
        "c_res_cond": consistency.c_res(resources_cond),
        "ece_10bin": calibration.ece(conf01, corr) if conf01 else float("nan"),
        "auroc": (calibration.auroc(conf01, corr) or float("nan")) if conf01 else float("nan"),
        "brier": calibration.brier(conf01, corr) if conf01 else float("nan"),
        "tokens_out_mean": _mean(r["tokens_out"] for r in rows),
        "chars_out_mean": _mean(r["chars_out"] for r in rows),
        "chars_out_reasoning_mean": _mean(r["chars_out_reasoning"] for r in rows),
        "gpu_s_mean": _mean(r["gpu_seconds"] for r in rows),
    })
    return out


def _report(rows: list[dict], cells: list[dict]) -> str:
    lines = [
        f"# REPORT — {rows[0]['exp_id']}",
        "",
        f"{len(rows)} rollouts, {len({r['task_id'] for r in rows})} tasks, "
        f"{len(cells)} cells, model `{rows[0]['model_id']}`, "
        f"benchmark `{rows[0]['benchmark']}` ({rows[0]['band']}).",
        "",
        "| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c in sorted(cells, key=lambda c: c["config_id"]):
        lines.append(
            f"| {c['config_id']} | {c['n_rollouts']} | {c['answered_rate']:.2f} "
            f"| {c['y_mean']:.3f} | {c['em_mean']:.2f} | {c['pass_at_k']:.2f} "
            f"| {c['c_out']:.2f} | {c['tokens_out_mean']:.0f} |"
        )
    reasons = Counter(r["finish_reason"] for r in rows)
    lines += ["", "Failure modes: " + ", ".join(f"{k}={v}" for k, v in reasons.most_common())]
    parse_fail = sum(r["n_parse_failures"] for r in rows)
    lines += [f"Parse failures (retried once each): {parse_fail}", ""]
    return "\n".join(lines)


def _failures_note(store: RolloutStore) -> str:
    n = store.n_failures_logged()
    return (f"\nAPI-error attempts logged (not in the panel; retried on resume): {n}\n"
            if n else "")


def aggregate(rollouts_dir: Path | str, results_dir: Path | str) -> dict[str, Path]:
    rollouts_dir, results_dir = Path(rollouts_dir), Path(results_dir)
    store = RolloutStore(rollouts_dir)
    rows = list(store.records())
    if not rows:
        raise ValueError(f"no rollouts in {rollouts_dir}")

    problems: list[str] = []
    for i, r in enumerate(rows):
        for p in validate_record(r):
            problems.append(f"row {i} ({r.get('rollout_key', '?')}): {p}")
    if problems:
        raise ValueError("panel-schema violations:\n  " + "\n  ".join(problems[:20]))

    results_dir.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(rows, schema_overrides=_DTYPES)
    panel_path = results_dir / "panel.parquet"
    df.write_parquet(panel_path)

    by_cell: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_cell[tuple(r[k] for k in CELL_KEY)].append(r)
    cells = [cell_metrics_row(cell_rows) for cell_rows in by_cell.values()]
    cells_path = results_dir / "cell_metrics.parquet"
    pl.DataFrame(cells).write_parquet(cells_path)

    index = {}
    for ref in sorted({r["manifest_ref"] for r in rows}):
        src = rollouts_dir / ref
        if src.exists():
            shutil.copy(src, results_dir / ref)
            index[ref] = json.loads(src.read_text())
        else:
            index[ref] = {"MISSING": True}  # a row that can't resolve is a bug (§1.4)
    (results_dir / "manifest_index.json").write_text(json.dumps(index, indent=2, sort_keys=True))

    (results_dir / "REPORT.md").write_text(_report(rows, cells) + _failures_note(store))
    return {
        "panel": panel_path,
        "cell_metrics": cells_path,
        "report": results_dir / "REPORT.md",
    }
