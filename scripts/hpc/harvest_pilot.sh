#!/bin/bash
# Wait for a pilot job to finish, then aggregate + verify + commit + push its
# slices. Login node only. One command, no timing to get right:
#
#   bash scripts/hpc/harvest_pilot.sh <jobid> <model_id>
#
# Blocks (polling every 30 s) until the job leaves the queue; refuses to
# harvest if any slice had api_errors (resubmit the same sbatch to resume,
# then re-run this).
set -euo pipefail
JOBID=${1:?usage: harvest_pilot.sh <jobid> <model_id>}
MODEL_ID=${2:?usage: harvest_pilot.sh <jobid> <model_id>}
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh

echo "[harvest] waiting for job $JOBID to leave the queue (Ctrl-C is safe — re-run later)..."
while squeue -j "$JOBID" -h 2>/dev/null | grep -q .; do sleep 30; done

LOG="slurm-${JOBID}.out"
[ -f "$LOG" ] || { echo "[harvest] $LOG not found — wrong jobid or wrong directory"; exit 1; }
echo "[harvest] job done:"
grep "\[run\]" "$LOG" || { echo "[harvest] no [run] lines — job died before running; inspect $LOG"; exit 1; }
if grep "\[run\]" "$LOG" | grep -qv "api_errors=0"; then
  echo "[harvest] api_errors>0 in a slice — resubmit the same sbatch (resume retries), then re-run this"
  exit 1
fi

shopt -s nullglob
DIRS=("$SCRATCH"/harnesslab/pilot/rollouts_"${MODEL_ID}"_*)
[ ${#DIRS[@]} -gt 0 ] || { echo "[harvest] no rollout dirs for $MODEL_ID on \$SCRATCH"; exit 1; }
for d in "${DIRS[@]}"; do
  n=$(basename "$d"); n=${n#rollouts_}
  python -m harnesslab.cli aggregate --rollouts "$d" --out "results/pilot_$n"
  python -m harnesslab.cli verify --panel "results/pilot_$n/panel.parquet"
done
git add results/
git commit -m "results: pilot ${MODEL_ID} (job ${JOBID})" || echo "[harvest] nothing new to commit"
git push
echo "[harvest] done — ${#DIRS[@]} slice(s) pushed"
