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


def _coerce(v: str):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return {"true": True, "false": False}.get(v.lower(), v)


def _overrides(pairs: list[str] | None) -> dict:
    out = {}
    for pair in pairs or []:
        key, _, value = pair.partition("=")
        if not _ or not key:
            raise SystemExit(f"--set expects key=value, got {pair!r}")
        out[key] = _coerce(value)
    return out


def _cmd_run(args) -> int:
    spec = experiment.from_yaml(args.exp, overrides=_overrides(args.set))
    if args.backend == "mock":
        from .client import MockClient

        client = MockClient(lambda messages, seed: "Answer: mock")
    else:
        from dotenv import load_dotenv

        from .client import MultiEndpointClient, OpenAICompatClient

        load_dotenv()
        api_key = os.environ.get(args.api_key_env, "EMPTY")
        served = args.model or spec.model_id
        urls = [u.strip() for u in args.base_url.split(",") if u.strip()]
        endpoints = [OpenAICompatClient(u, served, api_key) for u in urls]
        client = endpoints[0] if len(endpoints) == 1 else MultiEndpointClient(endpoints)
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


def _cmd_fits_check(args) -> int:
    from .fits import check_registry

    rows = check_registry(experiment.load_registry())
    bad = False
    print(f"{'model_id':22} {'tier':4} {'params_B':>9} {'declared':14} {'computed':14}")
    for r in rows:
        flag = "" if r["ok"] else "  << MISMATCH"
        bad = bad or not r["ok"]
        print(f"{r['model_id']:22} {r['tier']:4} {str(r['params_b_total'] or '?'):>9} "
              f"{r['declared']:14} {r['computed']:14}{flag}")
    return 1 if bad else 0


def _cmd_budget(args) -> int:
    spec = experiment.from_yaml(args.exp, overrides=_overrides(args.set))
    n_tasks = spec.n_tasks or args.n_tasks
    n = len(spec.configs) * n_tasks * spec.k_seeds
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
    p.add_argument("--base-url", default="http://localhost:8001/v1",
                   help="endpoint URL; comma-separate several for round-robin (4-server nodes)")
    p.add_argument("--model", default=None, help="served model name (defaults to spec model_id)")
    p.add_argument("--api-key-env", default="BLABLADOR_API_KEY")
    p.add_argument("--set", action="append", metavar="KEY=VALUE",
                   help="override a spec field (repeatable), e.g. --set benchmark=gsm8k")
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
    p.add_argument("--set", action="append", metavar="KEY=VALUE")
    p.set_defaults(fn=_cmd_budget)

    p = sub.add_parser("fits-check", help="params x dtype vs GH200 memory -> serving_mode")
    p.set_defaults(fn=_cmd_fits_check)

    p = sub.add_parser("verify", help="schema-exactness + key-uniqueness of a panel")
    p.add_argument("--panel", required=True)
    p.set_defaults(fn=_cmd_verify)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
