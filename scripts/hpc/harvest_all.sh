#!/bin/bash
# Aggregate EVERY rollout store on $SCRATCH into results/, verify each panel,
# then commit and push. Login node. Idempotent — re-running just refreshes the
# snapshots, so this is the safe "make git match the cluster" button.
#
#   bash scripts/hpc/harvest_all.sh                 # everything, commit + push
#   ONLY=padding bash scripts/hpc/harvest_all.sh    # substring filter on the store path
#   NO_COMMIT=1 bash scripts/hpc/harvest_all.sh     # aggregate + verify only
#
# Task scope is derived per store from its own spec (--task-scope auto), so a
# capped slice (HotpotQA n_tasks=3000) drops its out-of-scope orphans instead
# of shipping partially-covered cells. Harvesting a LIVE store is fine: the
# store is append-only, so you get a consistent snapshot of a growing run.
set -uo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh
: "${SCRATCH:?SCRATCH unset — run 'jutil env activate -p <project>'}"

ONLY=${ONLY:-}
ok=0; failed=""; skipped=""
for d in "$SCRATCH"/harnesslab/*/rollouts_*; do
  [ -f "$d/rollouts.jsonl" ] || continue
  rel="${d#"$SCRATCH"/harnesslab/}"
  [ -n "$ONLY" ] && [[ "$rel" != *"$ONLY"* ]] && continue
  case "$rel" in *_bad_*) skipped+=" $rel"; continue;; esac   # quarantined runs
  exp="${rel%%/*}"; slice="${rel#*/rollouts_}"
  out="results/${exp}_${slice}"
  echo
  echo "=== $rel -> $out"
  # quote the glob: polars expands panel*.parquet itself (census slices ship
  # as sharded parts, ADR 20); letting the shell expand it would pass argparse
  # several --panel values and abort the harvest.
  if python -m harnesslab.cli aggregate --rollouts "$d" --out "$out" --task-scope auto \
     && python -m harnesslab.cli verify --panel "$out/panel*.parquet"; then
    ok=$((ok + 1))
  else
    failed+=" $rel"
  fi
done

echo
echo "[harvest-all] harvested $ok slice(s)"
[ -n "$skipped" ] && echo "[harvest-all] skipped (quarantined):$skipped"
[ -n "$failed" ] && echo "[harvest-all] FAILED:$failed"
[ "$ok" -gt 0 ] || { echo "[harvest-all] nothing harvested"; exit 1; }

if [ "${NO_COMMIT:-0}" = "1" ]; then
  echo "[harvest-all] NO_COMMIT=1 — leaving results/ uncommitted"
  exit 0
fi
git add results/
git commit -m "results: harvest snapshot ($ok slices)" || echo "[harvest-all] nothing new to commit"
git push
