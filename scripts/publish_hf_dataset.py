"""Publish the contract-compliant results/ tree as a HuggingFace dataset.

Uploads panels (rollout-level, NO raw text by construction), cell metrics,
manifests, REPORTs, plus the two schema files — everything a reuser needs to
consume the data *correctly*, including the causal-role registry that says
which columns must never be used as covariates.

    export HF_TOKEN=hf_...           # write token; never committed (.env ok too)
    python scripts/publish_hf_dataset.py --repo <user>/harnesslab-panels
    python scripts/publish_hf_dataset.py --repo ... --public   # default: private

Re-running uploads incrementally (same repo, new commit). Raw rollout JSONL
never leaves $SCRATCH — this script only ever reads results/ and schema/.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CARD_TEMPLATE = """\
---
license: cc-by-4.0
tags:
  - agent-harness
  - causal-inference
  - factorial-experiment
  - llm-evaluation
pretty_name: HarnessLab panels
---

# HarnessLab — factorial agent-harness panels

Rollout-level panels from a randomized **2^5 factorial** over agent-scaffold
components — P (planning), T (tool use), M (memory), SR (structured
reasoning), R (reflection) — run with repeated sampling seeds on self-hosted
open-weight models (vLLM, JUPITER supercomputer). Every configuration x task
x seed cell is observed; execution order is randomized within jobs; grading
is deterministic (no LLM judge anywhere in the outcome).

- **Unit of observation**: one rollout = (model, benchmark, config, ordering,
  template, padding, temp) x task x seed. No prompt/completion text is
  included, by contract — trajectories are summarized as action-type
  sequences and count/cost columns.
- **Layout**: `slices/<experiment>_<model>_<benchmark>/panel*.parquet`
  (sharded when large) + `cell_metrics.parquet` + `manifest*.json` +
  `REPORT.md` per slice.
- **Provenance**: every row's `manifest_ref` resolves to a manifest with the
  git SHA, model HF repo + pinned revision, vLLM version, sampling params,
  content-hashes of every prompt-template block, and the task-list sha256.

## Read this before using the data

`schema/column_roles.yaml` assigns every column one causal role. Two rules
are load-bearing:

1. **Post-treatment columns are never covariates.** `n_turns`, `tokens_*`,
   `chars_*`, `n_tool_calls`, `n_parse_failures`, `wall_s`, `gpu_seconds`,
   `action_seq` are mediators/cost outcomes. Conditioning on them opens
   collider paths in an otherwise cleanly randomized design.
2. **Fixed-factor scope.** Models, families, benchmarks, and bands are fixed
   factors: effects are identified *within* each (model, band); contrasts
   *across* families are observational comparisons of bundled packages
   (capability x post-training vintage x tokenizer x template delivery).

Y-decomposition: use `y` (primary), `answered` (grader-interface channel),
and success-given-answered (conditions on a post-treatment event — cautious)
together, not `y` alone.

## Loading

```python
import polars as pl
panel = pl.read_parquet("hf://datasets/{repo}/slices/*/panel*.parquet")
```

or per slice with `datasets`:

```python
from datasets import load_dataset
ds = load_dataset("{repo}", data_files="slices/mvp_grid_qwen_3_5_9b_math/panel*.parquet")
```

## Source & citation

Code, task lists, schemas, decision log: the HarnessDML repository
(git SHA at publish time: `{sha}`). Design synthesizes three lines of prior
work: component factorials (arXiv:2605.05716), attribution-controlled harness
evaluation (arXiv:2606.12344), and distributional reliability outcomes
(arXiv:2602.16666); see the repo's ESTIMANDS.md and DATASHEET.md for the
estimand and scope statements.

Published {date} · {n_slices} slices · {n_rows:,} rollouts
"""


def build_card(repo: str, n_slices: int, n_rows: int, sha: str) -> str:
    return CARD_TEMPLATE.format(
        repo=repo, n_slices=n_slices, n_rows=n_rows, sha=sha,
        date=datetime.now(timezone.utc).date().isoformat(),
    )


def count_rows(results: Path) -> tuple[int, int]:
    import polars as pl

    n_slices, n_rows = 0, 0
    for d in sorted(results.iterdir()):
        parts = sorted(d.glob("panel*.parquet")) if d.is_dir() else []
        if not parts:
            continue
        n_slices += 1
        n_rows += sum(pl.scan_parquet(p).select(pl.len()).collect().item() for p in parts)
    return n_slices, n_rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, help="e.g. <user>/harnesslab-panels")
    ap.add_argument("--public", action="store_true", help="default is a private repo")
    ap.add_argument("--dry-run", action="store_true", help="build the card, upload nothing")
    args = ap.parse_args()

    from huggingface_hub import HfApi

    results = ROOT / "results"
    n_slices, n_rows = count_rows(results)
    if not n_slices:
        print("nothing to publish: no panel parquets under results/", file=sys.stderr)
        return 2
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip() or "unknown"
    card = build_card(args.repo, n_slices, n_rows, sha)
    print(f"[publish] {n_slices} slices, {n_rows:,} rollouts, repo={args.repo} "
          f"({'public' if args.public else 'private'})")
    if args.dry_run:
        print(card)
        return 0

    api = HfApi()  # token from HF_TOKEN / stored login
    api.create_repo(args.repo, repo_type="dataset", private=not args.public,
                    exist_ok=True)
    api.upload_file(path_or_fileobj=card.encode(), path_in_repo="README.md",
                    repo_id=args.repo, repo_type="dataset")
    api.upload_folder(folder_path=str(ROOT / "schema"), path_in_repo="schema",
                      repo_id=args.repo, repo_type="dataset",
                      commit_message=f"schema @ {sha[:12]}")
    api.upload_folder(
        folder_path=str(results), path_in_repo="slices",
        repo_id=args.repo, repo_type="dataset",
        commit_message=f"results @ {sha[:12]} ({n_rows:,} rollouts)",
        ignore_patterns=[".gitkeep"],
    )
    print(f"[publish] done -> https://huggingface.co/datasets/{args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
