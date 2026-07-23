"""harnesslab CLI: run | budget | status | aggregate | verify (§3).

`budget` refuses to plan any experiment lacking a measured pilot-throughput
constant (§7). `run --backend mock` exists for smoke-tests only; live runs
use --backend openai against a vLLM/Blablador endpoint.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from . import aggregate as agg
from . import experiment, panel
from .store import RolloutStore


def _cmd_run(args) -> int:
    spec = experiment.from_yaml(args.exp)
    if args.backend == "mock":
        from .client import MockClient

        client = MockClient(lambda messages, seed: "Answer: mock")
    else:
        from dotenv import load_dotenv

        from .client import OpenAICompatClient

        load_dotenv()
        api_key = os.environ.get(args.api_key_env, "EMPTY")
        client = OpenAICompatClient(args.base_url, args.model or spec.model_id, api_key)
    from .agent.runner import run_experiment

    summary = asyncio.run(run_experiment(spec, client, args.out))
    print(
        f"[run] {spec.exp_id}: total={summary.total} "
        f"already_done={summary.already_done} ran={summary.ran} "
        f"manifest={summary.manifest_ref}"
    )
    return 0


def _cmd_aggregate(args) -> int:
    paths = agg.aggregate(args.rollouts, args.out)
    for name, p in paths.items():
        print(f"[aggregate] {name}: {p}")
    return 0


def _cmd_status(args) -> int:
    store = RolloutStore(args.rollouts)
    print(f"[status] {len(store)} rollouts complete in {args.rollouts} "
          f"({store.n_corrupt} corrupt lines ignored)")
    return 0


def _cmd_budget(args) -> int:
    spec = experiment.from_yaml(args.exp)
    n = len(spec.configs) * args.n_tasks * spec.k_seeds
    if spec.throughput_rollouts_per_node_hour is None:
        print(
            f"[budget] REFUSED: {spec.exp_id} has no pilot-throughput constant "
            "(throughput_rollouts_per_node_hour). Run the pilot first (§7).",
            file=sys.stderr,
        )
        return 2
    hours = n / spec.throughput_rollouts_per_node_hour
    print(f"[budget] {spec.exp_id}: {n} rollouts ≈ {hours:.1f} node-hours "
          f"at {spec.throughput_rollouts_per_node_hour:.0f} rollouts/node-hour")
    return 0


def _cmd_verify(args) -> int:
    df = panel.load_panel(args.panel)
    problems = []
    expected = set(panel.panel_columns())
    if set(df.columns) != expected:
        problems.append(f"columns differ from schema: ±{set(df.columns) ^ expected}")
    if df["rollout_key"].n_unique() != len(df):
        problems.append("duplicate rollout_key values")
    if problems:
        print("[verify] FAILED:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 1
    print(f"[verify] OK: {len(df)} rows, schema-exact, keys unique")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="harnesslab", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="execute an experiment spec")
    p.add_argument("--exp", required=True)
    p.add_argument("--out", required=True, help="rollout store directory ($SCRATCH side)")
    p.add_argument("--backend", choices=("mock", "openai"), default="openai")
    p.add_argument("--base-url", default="http://localhost:8001/v1")
    p.add_argument("--model", default=None, help="served model name (defaults to spec model_id)")
    p.add_argument("--api-key-env", default="BLABLADOR_API_KEY")
    p.set_defaults(fn=_cmd_run)

    p = sub.add_parser("aggregate", help="rollouts.jsonl -> results/<exp_id>/")
    p.add_argument("--rollouts", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=_cmd_aggregate)

    p = sub.add_parser("status", help="completed-rollout count for a store")
    p.add_argument("--rollouts", required=True)
    p.set_defaults(fn=_cmd_status)

    p = sub.add_parser("budget", help="node-hour estimate (refuses without pilot constant)")
    p.add_argument("--exp", required=True)
    p.add_argument("--n-tasks", type=int, default=100)
    p.set_defaults(fn=_cmd_budget)

    p = sub.add_parser("verify", help="schema-exactness + key-uniqueness of a panel")
    p.add_argument("--panel", required=True)
    p.set_defaults(fn=_cmd_verify)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
