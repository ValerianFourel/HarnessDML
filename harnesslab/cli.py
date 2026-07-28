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
        served = args.model or experiment.served_model_name(spec)
        urls = [u.strip() for u in args.base_url.split(",") if u.strip()]
        endpoints = [
            OpenAICompatClient(u, served, api_key,
                               chat_template_kwargs=spec.chat_template_kwargs)
            for u in urls
        ]
        client = endpoints[0] if len(endpoints) == 1 else MultiEndpointClient(endpoints)
    from .agent.runner import run_experiment

    summary = asyncio.run(run_experiment(spec, client, args.out))
    print(
        f"[run] {spec.exp_id}: total={summary.total} "
        f"already_done={summary.already_done} ran={summary.ran} "
        f"api_errors={summary.api_errors} manifest={summary.manifest_ref}"
    )
    if summary.api_errors:
        print(f"[run] WARNING: {summary.api_errors} rollouts hit terminal API errors — "
              "NOT persisted; fix the endpoint and resubmit (resume retries them)",
              file=sys.stderr)
        return 3
    return 0


def _keep_ids(tasks: str | None, n_tasks: int | None) -> set[str] | None:
    if not tasks:
        return None
    from harnesslab.tasks import load_tasks
    ids = [t["task_id"] for t in load_tasks(tasks)]
    if n_tasks is not None:
        ids = ids[:n_tasks]
    return set(ids)


def _cmd_aggregate(args) -> int:
    keep = _keep_ids(args.tasks, args.n_tasks)
    if keep is None and args.task_scope == "auto":
        from pathlib import Path

        from . import progress as prog

        keep, why = prog.auto_scope(Path(args.rollouts))
        print(f"[aggregate] task-scope auto — {why}")
    paths = agg.aggregate(args.rollouts, args.out, keep_task_ids=keep, dedupe=args.dedupe)
    for name, p in paths.items():
        print(f"[aggregate] {name}: {p}")
    return 0


def _cmd_status(args) -> int:
    store = RolloutStore(args.rollouts)
    print(f"[status] {len(store)} rollouts complete in {args.rollouts} "
          f"({store.n_corrupt} corrupt lines ignored)")
    keep = _keep_ids(args.tasks, args.n_tasks)
    if keep is not None:
        from pathlib import Path

        from . import progress as prog

        s = prog.scan_store(Path(args.rollouts) / "rollouts.jsonl", keep)
        print(f"[status] in scope: {s['unique']} unique (cell, task, seed) of "
              f"{s['in_scope']} in-scope rows; {s['orphans']} out-of-scope "
              f"(dropped at harvest), {s['dupes']} duplicate")
    return 0


def _cmd_roster(args) -> int:
    from pathlib import Path

    from . import progress as prog

    root = Path(args.root or os.path.join(os.environ.get("SCRATCH", ""), "harnesslab"))
    rows = prog.walk(root, deep=args.deep, use_cache=not args.fresh) if root.is_dir() else []
    if not root.is_dir():
        print(f"[roster] no rollout root at {root} — showing rulings only", file=sys.stderr)
    print(prog.roster(rows, prog.load_gates(), experiment.load_registry(), deep=args.deep))
    return 0


def _cmd_progress(args) -> int:
    from pathlib import Path

    from . import progress as prog

    root = Path(args.root or os.path.join(os.environ.get("SCRATCH", ""), "harnesslab"))
    if not root.is_dir():
        print(f"[progress] no such rollout root: {root} (pass --root)", file=sys.stderr)
        return 2
    rows = prog.walk(root, deep=args.deep, only=args.only, use_cache=not args.fresh)
    if not rows:
        print(f"[progress] no rollout stores under {root}")
        return 0
    if args.roster:   # same walk, both views — a deep scan is minutes, do it once
        print(prog.roster(rows, prog.load_gates(), experiment.load_registry(),
                          deep=args.deep))
        print()
    print(prog.format_table(rows, deep=args.deep))
    print()
    print(prog.summarize(rows, deep=args.deep, gates=prog.load_gates()))
    if not args.deep:
        print("\n(counts are raw lines; --deep reads the stores for in-scope, "
              "de-duplicated progress — DONE? and ORPHANS? resolve only there)")
    if args.only:
        # gaps() would call every slice the filter hid "NO STORE"
        print(f"\n(--only {args.only}: gate coverage not evaluated — run without it)")
        return 0
    missing = prog.gaps(rows, prog.load_gates())
    if missing:
        print("\nGATED BUT NOT FINISHED (configs/gates.yaml):")
        for g in missing:
            tgt = f"{g['have']}/{g['target']}" if g["target"] else "-"
            print(f"  {g['model']:22.22} {g['bench']:9.9} {g['state']:9} {tgt:>18}  {g['note']}")
        print("\n  each is one chain link:  " + missing[0]["submit"])
        print("  (a slice too big for one 11.5 h window runs as a chain — "
              "see scripts/hpc/submit_census*.sh)")
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
    p.add_argument("--tasks", default=None,
                   help="committed task list; drop rollouts whose task_id is outside "
                        "the first --n-tasks of it (cleans orphans from a capped slice)")
    p.add_argument("--n-tasks", type=int, default=None,
                   help="with --tasks, keep only the first N task_ids (e.g. 3000 for HotpotQA)")
    p.add_argument("--task-scope", choices=("none", "auto"), default="none",
                   help="'auto' derives the task list and cap from the store path's "
                        "own experiment spec (what harvest_all.sh uses)")
    p.add_argument("--dedupe", action="store_true",
                   help="keep the first row per (cell, task, seed); use when a rollout-key "
                        "schema change re-ran finished work (ADR 22)")
    p.set_defaults(fn=_cmd_aggregate)

    p = sub.add_parser("status", help="completed-rollout count for a store")
    p.add_argument("--rollouts", required=True)
    p.add_argument("--tasks", default=None,
                   help="committed task list; also report in-scope/orphan/duplicate counts")
    p.add_argument("--n-tasks", type=int, default=None,
                   help="with --tasks, in-scope means the first N task_ids")
    p.set_defaults(fn=_cmd_status)

    p = sub.add_parser("progress", help="per-slice progress vs each spec's own target")
    p.add_argument("--root", default=None,
                   help="rollout root (default $SCRATCH/harnesslab)")
    p.add_argument("--deep", action="store_true",
                   help="read the stores: in-scope, de-duplicated counts (minutes on a census)")
    p.add_argument("--only", default=None, help="substring filter on <exp>/rollouts_<model>_<bench>")
    p.add_argument("--roster", action="store_true",
                   help="also print the per-model roster (from the same scan)")
    p.add_argument("--fresh", action="store_true",
                   help="ignore the deep-scan cache and re-read every store")
    p.set_defaults(fn=_cmd_progress)

    p = sub.add_parser("roster", help="every registry model x band: gate ruling + progress")
    p.add_argument("--root", default=None, help="rollout root (default $SCRATCH/harnesslab)")
    p.add_argument("--deep", action="store_true", help="read the stores for true progress")
    p.add_argument("--fresh", action="store_true", help="ignore the deep-scan cache")
    p.set_defaults(fn=_cmd_roster)

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
