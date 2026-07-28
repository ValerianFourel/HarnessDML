#!/bin/bash
# Aggregate EVERY rollout store on $SCRATCH into results/, verify each panel,
# then commit and push. Login node. Idempotent — re-running just refreshes the
# snapshots, so this is the safe "make git match the cluster" button.
#
#   bash scripts/hpc/harvest_all.sh                 # everything, commit + push
#   ONLY=padding bash scripts/hpc/harvest_all.sh    # substring filter on the store path
#   NO_COMMIT=1 bash scripts/hpc/harvest_all.sh     # aggregate + verify only
#   DEDUPE=1 bash scripts/hpc/harvest_all.sh        # drop the ADR 22 re-key duplicates
#
# A full census slice aggregates ~700k rows into sharded parquet — minutes and
# tens of MB per slice. ONLY= a finished arm first; harvest census slices
# deliberately, as they complete.
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
  # quarantined runs, and the Phase-2 smoke slice: its 20 rollouts predate
  # `chars_out_reasoning` in the panel schema, so re-aggregating it fails the
  # schema check by design. It was a connectivity test, never a deliverable —
  # its original panel stays committed as history. Do NOT "fix" this by
  # backfilling missing columns: the loud failure is the schema guard working.
  case "$rel" in *_bad_*|smoke_live/*) skipped+=" $rel"; continue;; esac
  exp="${rel%%/*}"; slice="${rel#*/rollouts_}"
  out="results/${exp}_${slice}"
  echo
  echo "=== $rel -> $out"
  # quote the glob: polars expands panel*.parquet itself (census slices ship
  # as sharded parts, ADR 20); letting the shell expand it would pass argparse
  # several --panel values and abort the harvest.
  if python -m harnesslab.cli aggregate --rollouts "$d" --out "$out" --task-scope auto \
       ${DEDUPE:+--dedupe} \
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
