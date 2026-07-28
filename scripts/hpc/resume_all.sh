#!/bin/bash
# Resubmit a chain for every unfinished gated slice, sized from the work that
# is actually left. Login node. This is the answer to "everything stalled".
#
#   bash scripts/hpc/resume_all.sh            # plan, then submit
#   DRY=1 bash scripts/hpc/resume_all.sh      # print the plan, submit nothing
#   PER_LINK=60000 bash scripts/hpc/resume_all.sh   # fewer, longer chains
#
# Chains drain: they are submitted at a fixed length, links die at the health
# ceiling or hit the 11.5 h walltime, and when the last one exits the slice
# just stops. On 2026-07-27/28 all 18 in-flight slices stalled within a few
# hours of each other for exactly this reason. Re-running this is how you top
# them all up without hand-counting anything.
#
# SAFE TO RE-RUN. A slice that already has a running or queued link is
# SKIPPED — two writers on one store is the one thing the design forbids — and
# a chain that turns out to be longer than needed costs nothing: a surplus
# link finds no pending rollouts and exits in minutes.
set -uo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh
PER_LINK=${PER_LINK:-40000}

echo "[resume] planning from the deep scan (cached — only changed stores are re-read)"
PLAN=$(python -m harnesslab.cli plan --deep --per-link "$PER_LINK") || {
  echo "[resume] plan failed"; exit 1; }
[ -n "$PLAN" ] || { echo "[resume] nothing outstanding — every gated slice is DONE"; exit 0; }

# one line per slice: model  bench  spec  remaining  links
printf "%-22s %-9s %12s %6s\n" MODEL BENCH REMAINING LINKS
printf "%s\n" "$PLAN" | awk -F'\t' '{printf "%-22s %-9s %12d %6d\n", $1, $2, $4, $5}'
[ "${DRY:-0}" = "1" ] && { echo "[resume] DRY=1 — nothing submitted"; exit 0; }

RUNNING_NAMES=$(squeue -u "$USER" -h -o "%j" | sort -u)
submitted=0; skipped=0
while IFS=$'\t' read -r model bench spec remaining links; do
  [ -n "${model:-}" ] || continue
  name="hl-$model-$bench"
  if printf "%s\n" "$RUNNING_NAMES" | grep -qx "$name"; then
    echo "[resume] SKIP $name — already has a link in the queue (single writer)"
    skipped=$((skipped + 1)); continue
  fi
  dep=""; id=""
  for _ in $(seq 1 "$links"); do
    id=$(EXP="$spec" MODEL_ID="$model" BENCH="$bench" \
         sbatch --parsable --job-name "$name" \
                ${dep:+--dependency=afterany:$dep} slurm/run_experiment.sbatch) || break
    dep=$id
  done
  echo "[resume] $name: $links-link chain for $remaining rollouts, tail $dep"
  submitted=$((submitted + 1))
done <<< "$PLAN"

echo
echo "[resume] $submitted chains submitted, $skipped skipped (already queued)"
squeue -u "$USER" -h -o "%j" | sort | uniq -c | sort -rn | head -30
echo "[resume] watch: bash scripts/hpc/overview.sh"
