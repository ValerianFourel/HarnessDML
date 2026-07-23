"""Experiment runner: schedule → (skip done) → rollout → grade → store.

Emits panel-schema-exact rows (validated in aggregate and by the e2e test).
Randomized interleaving per §4.3.1; resume by construction via the store.
"""

from __future__ import annotations

import asyncio
import os
import socket
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .. import graders, schedule
from ..client.base import ChatClient
from ..components import compose
from ..experiment import CellConfig, ExperimentSpec
from ..manifest import write_manifest
from ..store import RolloutStore, make_rollout_key
from ..tasks import load_tasks
from ..tools import DocStore, ToolBox
from .loop import run_rollout


@dataclass
class RunSummary:
    total: int
    already_done: int
    ran: int
    manifest_ref: str
    api_errors: int = 0  # infra failures — logged, NOT persisted, retried on resume


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _server_uptime_s() -> float:
    start = os.environ.get("HARNESSLAB_SERVER_START_TS")
    return max(0.0, time.time() - float(start)) if start else 0.0


def _vllm_version() -> str | None:
    """Serving-stack provenance (§1.4). On JUPITER the client venv is the
    serving venv; None on mock/dev environments without vLLM installed."""
    try:
        from importlib.metadata import version

        return version("vllm")
    except Exception:  # noqa: BLE001
        return None


def _toolbox_for(spec: ExperimentSpec, cfg: CellConfig, task: dict) -> ToolBox | None:
    if "T" not in cfg.components:
        return None  # no tools without T; QA becomes closed-book (§4.2 note)
    if spec.family == "qa":
        return ToolBox("qa", DocStore([tuple(p) for p in task["paragraphs"]]))
    return ToolBox("math")


def build_row(
    spec: ExperimentSpec,
    cfg: CellConfig,
    task: dict,
    seed: int,
    trace,
    y: float,
    em: bool,
    grader_path: str,
    *,
    run_id: str,
    manifest_ref: str,
    ts_start: str,
) -> dict:
    comps = cfg.components
    return {
        "rollout_key": make_rollout_key(spec.cell_dict(cfg), task["task_id"], seed),
        "run_id": run_id,
        "exp_id": spec.exp_id,
        "manifest_ref": manifest_ref,
        "node": socket.gethostname(),
        "ts_start": ts_start,
        "ts_end": _now_iso(),
        "server_uptime_s": _server_uptime_s(),
        "grader_path": grader_path,
        "seed": seed,
        "confidence_source": trace.confidence_source,
        "comp_P": "P" in comps,
        "comp_T": "T" in comps,
        "comp_M": "M" in comps,
        "comp_SR": "SR" in comps,
        "comp_R": "R" in comps,
        "config_id": cfg.config_id,
        "ordering_id": cfg.ordering_id,
        "template_id": cfg.template_id,
        "model_id": spec.model_id,
        "model_family": spec.model_family,
        "model_scale_b": spec.model_scale_b,
        "benchmark": spec.benchmark,
        "band": spec.band,
        "temp": spec.temp,
        "top_p": spec.top_p,
        "system_role_mode": spec.system_role_mode,
        "step_cap": spec.step_cap,
        "max_new_tokens_step": spec.max_new_tokens_step,
        "task_id": task["task_id"],
        "task_difficulty_calib": None,  # disjoint calibration slice only (§5)
        "y": y,
        "em": em,
        "answered": trace.answered,
        "finish_reason": trace.finish_reason,
        "confidence": trace.confidence,
        "n_turns": trace.n_turns,
        "n_tool_calls": trace.n_tool_calls,
        "n_parse_failures": trace.n_parse_failures,
        "tokens_in": trace.tokens_in,
        "tokens_out": trace.tokens_out,
        "chars_in": trace.chars_in,
        "chars_out": trace.chars_out,
        "chars_out_reasoning": trace.chars_out_reasoning,
        "wall_s": trace.wall_s,
        "gpu_seconds": trace.wall_s * float(os.environ.get("HARNESSLAB_GPU_PER_ROLLOUT", "0")),
        "latency_ms_mean": statistics.mean(trace.latencies_ms) if trace.latencies_ms else 0.0,
        "action_seq": ">".join(trace.action_seq),
    }


async def run_experiment(
    spec: ExperimentSpec,
    client: ChatClient,
    out_dir: Path | str,
    run_id: str | None = None,
) -> RunSummary:
    out_dir = Path(out_dir)
    run_id = run_id or os.environ.get("SLURM_JOB_ID") or f"local-{int(time.time())}"
    task_list = load_tasks(spec.tasks_file)
    if spec.n_tasks:
        task_list = task_list[: spec.n_tasks]  # committed order — deterministic slice
    tasks = {t["task_id"]: t for t in task_list}
    store = RolloutStore(out_dir)

    composed_cache = {
        cfg: compose(
            spec.family,
            cfg.components,
            ordering_id=cfg.ordering_id,
            template_id=cfg.template_id,
            coupled_submission=spec.coupled_submission,
            padding_components=cfg.padding_components,
        )
        for cfg in spec.configs
    }
    template_hashes = {
        cfg.config_id: composed_cache[cfg].block_hashes for cfg in spec.configs
    }
    manifest_path = write_manifest(
        out_dir,
        exp_id=spec.exp_id,
        exp_config={
            "benchmark": spec.benchmark, "model_id": spec.model_id,
            "configs": [c.config_id for c in spec.configs], "k_seeds": spec.k_seeds,
            "temp": spec.temp, "top_p": spec.top_p, "schedule_seed": spec.schedule_seed,
            "coupled_submission": spec.coupled_submission,
        },
        model={"model_id": spec.model_id, "family": spec.model_family,
               "hf_id": spec.model_hf_id, "revision": spec.model_revision},
        sampling={"temperature": spec.temp, "top_p": spec.top_p,
                  "max_new_tokens_step": spec.max_new_tokens_step, "seeds": spec.seeds},
        template_hashes=template_hashes,
        client_info={"type": type(client).__name__, "vllm_version": _vllm_version()},
        extra={"run_id": run_id},
    )
    manifest_ref = manifest_path.name

    triples = [
        (cfg, task_id, seed)
        for cfg in spec.configs
        for task_id in tasks
        for seed in spec.seeds
    ]
    queue = schedule.interleave(triples, spec.schedule_seed)
    pending = [
        (cfg, task_id, seed)
        for cfg, task_id, seed in queue
        if not store.is_done(make_rollout_key(spec.cell_dict(cfg), task_id, seed))
    ]

    sem = asyncio.Semaphore(spec.concurrency)
    api_errors = 0

    async def worker(cfg: CellConfig, task_id: str, seed: int) -> None:
        nonlocal api_errors
        async with sem:
            task = tasks[task_id]
            ts_start = _now_iso()
            trace = await run_rollout(
                client,
                composed_cache[cfg].text,
                task["question"],
                _toolbox_for(spec, cfg, task),
                step_cap=spec.step_cap,
                max_new_tokens=spec.max_new_tokens_step,
                temperature=spec.temp,
                top_p=spec.top_p,
                seed=seed,
                system_role_mode=spec.system_role_mode,
                timeout_s=spec.timeout_s,
                elicit_confidence=spec.elicit_confidence,
            )
            y, em, grader_path = graders.grade_rollout(spec.benchmark, trace.answer, task)
            row = build_row(
                spec, cfg, task, seed, trace, y, em, grader_path,
                run_id=run_id, manifest_ref=manifest_ref, ts_start=ts_start,
            )
            if trace.finish_reason == "api_error":
                api_errors += 1  # infra, not an outcome: keep pending, log only
                store.append_failure(row)
                return
            store.append(row)

    await asyncio.gather(*(worker(*item) for item in pending))
    return RunSummary(
        total=len(triples),
        already_done=len(triples) - len(pending),
        ran=len(pending),
        manifest_ref=manifest_ref,
        api_errors=api_errors,
    )
