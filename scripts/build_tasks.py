"""Build the committed task lists (§4.4): seeded N=100 per (benchmark, band).

Runs LOCALLY or on a JUPITER login node (network needed once):

    uv run --extra data python scripts/build_tasks.py --all
    uv run --extra data python scripts/build_tasks.py --benchmark gsm8k

Writes, per benchmark, into configs/tasks/:
  <benchmark>.jsonl      normalized tasks (question, golds, hermetic paragraphs)
  <benchmark>_ids.json   the committed ID list
  <benchmark>_meta.json  dataset id/split/seed/filters — provenance for DATASHEET

Compute nodes never touch these builders — they read the committed jsonl only.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from harnesslab.graders.math_sympy import extract_boxed
from harnesslab.graders.numeric import gold_from_gsm8k

OUT_DIR = Path(__file__).resolve().parents[1] / "configs" / "tasks"
DEFAULT_SEED = 20260723
DEFAULT_N = 100

# candidate HF dataset ids, tried in order (hub ids drift; failures are loud)
SOURCES = {
    "hotpotqa": [("hotpotqa/hotpot_qa", "distractor", "validation"),
                 ("hotpot_qa", "distractor", "validation")],
    "musique": [("dgslibisey/MuSiQue", None, "validation"),
                ("StonyBrookNLP/musique", "answerable", "validation")],
    "gsm8k": [("openai/gsm8k", "main", "test"), ("gsm8k", "main", "test")],
    "math": [("HuggingFaceH4/MATH-500", None, "test")],
}


def sample_indices(n_total: int, n: int, seed: int) -> list[int]:
    """Deterministic seeded sample, ascending (stable committed order)."""
    return sorted(random.Random(seed).sample(range(n_total), min(n, n_total)))


def extension_indices(pool: list[int], prior: set[int], n_extra: int, seed: int) -> list[int]:
    """Seeded sample of n_extra NEW pool indices, excluding prior — the
    committed list stays a strict superset (existing rollouts keep resuming)."""
    remaining = [i for i in pool if i not in prior]
    return [remaining[j] for j in sample_indices(len(remaining), n_extra, seed)]


def _load_first(benchmark: str):
    from datasets import load_dataset

    errors = []
    for dataset_id, config, split in SOURCES[benchmark]:
        try:
            ds = load_dataset(dataset_id, config, split=split)
            return ds, {"dataset_id": dataset_id, "config": config, "split": split}
        except Exception as exc:  # noqa: BLE001 — try next candidate, report all
            errors.append(f"{dataset_id}: {type(exc).__name__}: {exc}")
    raise RuntimeError(f"{benchmark}: all sources failed:\n  " + "\n  ".join(errors))


def _norm_hotpotqa(item: dict, idx: int) -> dict:
    ctx = item["context"]
    return {
        "task_id": item.get("id") or f"hotpotqa-{idx:05d}",
        "question": item["question"],
        "answers": [item["answer"]],
        "paragraphs": [[t, " ".join(s)] for t, s in zip(ctx["title"], ctx["sentences"])],
    }


def _norm_musique(item: dict, idx: int) -> dict:
    answers = [item["answer"], *item.get("answer_aliases", [])]
    return {
        "task_id": item.get("id") or f"musique-{idx:05d}",
        "question": item["question"],
        "answers": [a for a in answers if a],
        "paragraphs": [[p["title"], p["paragraph_text"]] for p in item["paragraphs"]],
    }


def _norm_gsm8k(item: dict, idx: int) -> dict:
    return {
        "task_id": f"gsm8k-test-{idx:05d}",
        "question": item["question"],
        "gold": gold_from_gsm8k(item["answer"]),
    }


def _norm_math(item: dict, idx: int) -> dict:
    gold = item.get("answer") or extract_boxed(item.get("solution", ""))
    if not gold:
        raise ValueError("no gold answer")
    return {
        "task_id": item.get("unique_id") or f"math-{idx:05d}",
        "question": item["problem"],
        "gold": gold,
    }


def _math_level(item: dict) -> int | None:
    lvl = item.get("level")
    if lvl is None:
        return None
    if isinstance(lvl, int):
        return lvl
    digits = "".join(c for c in str(lvl) if c.isdigit())
    return int(digits) if digits else None


NORMALIZERS = {"hotpotqa": _norm_hotpotqa, "musique": _norm_musique,
               "gsm8k": _norm_gsm8k, "math": _norm_math}


def build(benchmark: str, n: int, seed: int) -> dict:
    ds, source = _load_first(benchmark)
    indices = list(range(len(ds)))
    filters = {}
    if benchmark == "math":  # hard band = levels 4–5 (§4.4)
        indices = [i for i in indices if (_math_level(ds[i]) or 0) >= 4]
        filters["level"] = ">=4"

    chosen = [indices[j] for j in sample_indices(len(indices), n, seed)]
    tasks, skipped = [], 0
    for idx in chosen:
        try:
            tasks.append(NORMALIZERS[benchmark](ds[idx], idx))
        except (KeyError, ValueError):
            skipped += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / f"{benchmark}.jsonl", "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    (OUT_DIR / f"{benchmark}_ids.json").write_text(
        json.dumps([t["task_id"] for t in tasks], indent=1)
    )
    meta = {
        **source, "seed": seed, "n_requested": n, "n_built": len(tasks),
        "n_skipped": skipped, "filters": filters, "pool_size": len(indices),
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (OUT_DIR / f"{benchmark}_meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def extend(benchmark: str, target_n: int, ext_seed: int) -> dict:
    """Grow the committed list to target_n by APPENDING a seeded sample of
    unused pool tasks. The existing prefix is byte-identical afterwards, so
    every completed rollout keeps resuming; deep-eval jobs pay only the
    increment. Census: target_n >= pool size takes the whole remainder."""
    meta_path = OUT_DIR / f"{benchmark}_meta.json"
    jsonl_path = OUT_DIR / f"{benchmark}.jsonl"
    meta = json.loads(meta_path.read_text())
    existing_lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    n_existing = len(existing_lines)
    if target_n <= n_existing:
        return {**meta, "n_added": 0, "n_total": n_existing}

    ds, source = _load_first(benchmark)
    assert source["dataset_id"] == meta["dataset_id"], \
        f"{benchmark}: source drifted ({source['dataset_id']} != {meta['dataset_id']})"
    indices = list(range(len(ds)))
    if benchmark == "math":
        indices = [i for i in indices if (_math_level(ds[i]) or 0) >= 4]
    # the original chosen set is reproducible from the committed meta
    prior = {indices[j] for j in
             sample_indices(meta["pool_size"], meta["n_requested"], meta["seed"])}
    for ext in meta.get("extensions", []):  # prior extensions too
        prior |= set(ext["chosen_pool_indices"])

    chosen = extension_indices(indices, prior, target_n - n_existing, ext_seed)
    added, skipped = [], 0
    for idx in chosen:
        try:
            added.append(NORMALIZERS[benchmark](ds[idx], idx))
        except (KeyError, ValueError):
            skipped += 1
    with open(jsonl_path, "a", encoding="utf-8") as f:
        for t in added:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    # superset guarantee: the prefix must be untouched
    now_lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert now_lines[:n_existing] == existing_lines, "prefix changed — abort"

    ids = json.loads((OUT_DIR / f"{benchmark}_ids.json").read_text())
    ids += [t["task_id"] for t in added]
    (OUT_DIR / f"{benchmark}_ids.json").write_text(json.dumps(ids, indent=1))
    meta.setdefault("extensions", []).append({
        "seed": ext_seed, "target_n": target_n, "n_added": len(added),
        "n_skipped": skipped, "chosen_pool_indices": chosen,
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    meta_path.write_text(json.dumps(meta, indent=2))
    return {**meta, "n_added": len(added), "n_total": n_existing + len(added)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--benchmark", choices=sorted(SOURCES), default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--n", type=int, default=DEFAULT_N)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--extend", action="store_true",
                    help="grow the committed list to --n by appending (superset)")
    args = ap.parse_args()

    benchmarks = sorted(SOURCES) if args.all else [args.benchmark]
    if benchmarks == [None]:
        ap.error("--benchmark or --all required")
    failures = 0
    for b in benchmarks:
        try:
            if args.extend:
                meta = extend(b, args.n, args.seed)
                print(f"[tasks] {b}: +{meta['n_added']} -> {meta['n_total']} tasks "
                      f"(pool {meta['pool_size']})")
            else:
                meta = build(b, args.n, args.seed)
                print(f"[tasks] {b}: {meta['n_built']} tasks from {meta['dataset_id']} "
                      f"(pool {meta['pool_size']}, skipped {meta['n_skipped']})")
        except Exception as exc:  # noqa: BLE001 — build the rest, fail at exit
            failures += 1
            print(f"[tasks] {b}: FAILED — {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
