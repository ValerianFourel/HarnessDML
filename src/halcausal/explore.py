"""One-shot remote exploration of a HAL slice — "what exactly is inside".

Run ON THE CLUSTER (login node, network available):

    python -m halcausal.explore --slice taubench_airline --push

Pipeline (idempotent, resumable): download slice -> decrypt only missing ->
schema discovery (schema/SCHEMA.md + paths.json + suggested mapping) ->
raw-number JSONs -> manifest -> size-guarded git push. Local side pulls and
analyzes the JSONs; no cluster access needed.

Committed artifacts (all small):
- results/explore/<slice>/runs.json       one record per run file: sizes,
  top-level structure, every small config-like block verbatim (scalars only,
  long strings clipped, secret-looking keys redacted — the repo is public),
  collection sizes.
- results/explore/<slice>/aggregate.json  cross-run raw numbers: key presence,
  type consistency, collection-size stats, distinct-value counts per
  discovered config/result field (e.g. which models, reasoning efforts,
  scaffolds actually occur, and how often).
- schema/SCHEMA.md (+ paths.json, field_mapping.suggested.yaml)
- results/manifests/<run_id>.json

Exploration is schema-agnostic by construction: it captures whatever fields
exist without hardcoding any names (CLAUDE.md Phase-1 guardrail).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

from . import paths
from .etl import discover_schema
from .io import decrypt as dec
from .io import hf
from .io.manifest import new_run_id, write_manifest

_SECRET_RE = re.compile(r"api|key|token|secret|password|credential", re.I)
_SCALAR = (str, int, float, bool, type(None))


def _clip(v, max_str: int):
    if isinstance(v, str) and len(v) > max_str:
        return v[:max_str] + "…"
    return v


def _scalars(d: dict, max_str: int) -> dict:
    out = {}
    for k, v in d.items():
        if _SECRET_RE.search(str(k)):
            out[str(k)] = "«redacted»"
        elif isinstance(v, _SCALAR):
            out[str(k)] = _clip(v, max_str)
    return out


def summarize_run_file(path: Path, max_block_items: int = 120, max_str: int = 200) -> dict:
    """Schema-agnostic single-file summary: structure + small blocks verbatim."""
    doc = json.loads(path.read_text())
    rec: dict = {
        "file": path.name,
        "size_mb": round(path.stat().st_size / 1e6, 2),
        "benchmark_guess": hf.bucket_for(path.name),
        "top_level": {},
        "small_blocks": {},
        "collection_sizes": {},
    }
    if not isinstance(doc, dict):
        rec["top_level"]["<root>"] = {"type": type(doc).__name__}
        return rec

    for k, v in doc.items():
        entry: dict = {"type": type(v).__name__}
        if isinstance(v, dict):
            entry["n_keys"] = len(v)
        elif isinstance(v, list):
            entry["len"] = len(v)
        rec["top_level"][str(k)] = entry

        if isinstance(v, dict):
            if len(v) <= max_block_items:
                block = _scalars(v, max_str)
                for kk, vv in v.items():
                    if isinstance(vv, dict) and len(vv) <= max_block_items:
                        sub = _scalars(vv, max_str)
                        if sub:
                            block[str(kk)] = sub
                if block:
                    rec["small_blocks"][str(k)] = block
            else:
                rec["collection_sizes"][str(k)] = len(v)
        elif isinstance(v, list):
            rec["collection_sizes"][str(k)] = len(v)
    return rec


def aggregate(records: list[dict]) -> dict:
    """Cross-run raw numbers from per-file summaries."""
    n = len(records)
    key_presence: Counter = Counter()
    type_by_key: dict[str, Counter] = {}
    coll_sizes: dict[str, list[int]] = {}
    field_values: dict[str, Counter] = {}

    for r in records:
        for k, e in r["top_level"].items():
            key_presence[k] += 1
            type_by_key.setdefault(k, Counter())[e["type"]] += 1
        for k, s in r["collection_sizes"].items():
            coll_sizes.setdefault(k, []).append(s)
        for block, fields in r["small_blocks"].items():
            for f, v in fields.items():
                if isinstance(v, dict):
                    for f2, v2 in v.items():
                        field_values.setdefault(f"{block}.{f}.{f2}", Counter())[str(v2)[:80]] += 1
                else:
                    field_values.setdefault(f"{block}.{f}", Counter())[str(v)[:80]] += 1

    def _values(c: Counter, cap: int = 25) -> dict:
        if len(c) > cap:
            return {"n_distinct": len(c), "top5": dict(c.most_common(5))}
        return dict(c.most_common())

    return {
        "n_files": n,
        "total_mb": round(sum(r["size_mb"] for r in records), 1),
        "top_level_key_presence": {k: f"{v}/{n}" for k, v in key_presence.most_common()},
        "top_level_types": {k: dict(c) for k, c in sorted(type_by_key.items())},
        "collection_sizes": {
            k: {"min": min(v), "median": int(statistics.median(v)), "max": max(v), "sum": sum(v)}
            for k, v in sorted(coll_sizes.items())
        },
        "field_value_counts": {k: _values(c) for k, c in sorted(field_values.items())},
    }


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, check=check)


def push_artifacts(run_id: str) -> int:
    """git pull --rebase, stage results/+schema/, size guard, commit, push."""
    root = paths.repo_root()
    _git(root, "pull", "--rebase")
    _git(root, "add", "results/", "schema/")

    guard = subprocess.run(
        [sys.executable, "scripts/check_results_size.py", "--staged"], cwd=root
    )
    if guard.returncode:
        print("[explore] size guard FAILED — nothing committed", file=sys.stderr)
        return guard.returncode

    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root)
    if staged.returncode == 0:
        print("[explore] nothing new to commit")
        return 0
    _git(root, "commit", "-m", f"HPC explore: {run_id}")
    _git(root, "push")
    print(f"[explore] pushed — locally: git pull, then analyze run {run_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slice", dest="slice_", default=None, help="benchmark slice (default: configs/env.yaml first_slice)")
    ap.add_argument("--push", action="store_true", help="commit+push results/ and schema/ after the size guard")
    ap.add_argument("--no-download", action="store_true", help="offline: use already-downloaded zips")
    ap.add_argument("--max-file-gb", type=float, default=2.0, help="skip decrypted files above this size (listed, never silent)")
    args = ap.parse_args(argv)

    env_file = paths.configs_dir() / "env.yaml"
    env = yaml.safe_load(env_file.read_text()) if env_file.is_file() else {}
    slice_ = args.slice_ or env.get("first_slice", "taubench_airline")
    run_id = new_run_id()
    enc_dir = paths.data_dir() / "encrypted" / slice_

    if args.no_download:
        zips = sorted(enc_dir.glob("*.zip"))
    else:
        zips = hf.download_slice(slice_)  # resumable; hard-errors > 5 GB unconfirmed
    print(f"[explore] {len(zips)} zips in {enc_dir}")
    if not zips:
        print("[explore] no zips — wrong slice name or download failed", file=sys.stderr)
        return 2

    jsons, n_new = dec.decrypt_missing(enc_dir)
    print(f"[explore] decrypted {n_new} zips this run; {len(jsons)} json files present")

    md = discover_schema(enc_dir, max_file_gb=args.max_file_gb)
    print(f"[explore] schema report -> {md}")

    records, skipped = [], []
    for p in jsons:
        gb = p.stat().st_size / 1e9
        if gb > args.max_file_gb:
            skipped.append({"file": p.name, "why": f"{gb:.2f} GB > --max-file-gb {args.max_file_gb}"})
            continue
        try:
            records.append(summarize_run_file(p))
        except Exception as e:  # one bad file must not kill the sweep
            skipped.append({"file": p.name, "why": f"{type(e).__name__}: {e}"})

    agg = aggregate(records)
    agg.update({"run_id": run_id, "slice": slice_, "n_zips": len(zips),
                "n_json": len(jsons), "skipped": skipped})

    out_dir = paths.results_dir() / "explore" / slice_
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "runs.json").write_text(json.dumps(records, indent=1, default=str))
    (out_dir / "aggregate.json").write_text(json.dumps(agg, indent=1, default=str))

    write_manifest(
        run_id,
        counts={"zips": len(zips), "decrypted_json": len(jsons),
                "summarized": len(records), "skipped": len(skipped)},
        extra={"slice": slice_, "phase": "explore",
               "outputs": [f"results/explore/{slice_}/runs.json",
                           f"results/explore/{slice_}/aggregate.json",
                           "schema/SCHEMA.md"]},
    )

    print(f"[explore] {len(records)} runs summarized ({len(skipped)} skipped) -> {out_dir}")
    if args.push:
        return push_artifacts(run_id)
    print("[explore] not pushing (no --push). To ship:\n"
          "  git pull --rebase && git add results/ schema/ && "
          "python scripts/check_results_size.py --staged && "
          f'git commit -m "HPC explore: {run_id}" && git push')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
