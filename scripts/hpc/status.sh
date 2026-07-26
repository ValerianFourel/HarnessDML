#!/bin/bash
# One-shot "what is JUPITER doing" check. Login node.
#   bash scripts/hpc/status.sh
# Covers: jobs, recent outcomes, running-server health, all rollout stores +
# census total, and recent probe verdicts. Read-only; safe to run anytime.
set -uo pipefail
cd "$(dirname "$0")/../.." 2>/dev/null || true
source scripts/hpc/env.sh

echo "===== 1. JOBS ====="
printf "running: %s   pending: %s\n" \
  "$(squeue -u "$USER" -h -t R | wc -l)" "$(squeue -u "$USER" -h -t PD | wc -l)"
squeue -u "$USER" -o "%.11i %.8T %.24j %.9M %R" | head -12

echo; echo "===== 2. RECENT OUTCOMES (last 3h) ====="
sacct -u "$USER" --starttime now-3hours -o State%12 2>/dev/null \
  | grep -vE "State|---|\.ba|\.ex" | sort | uniq -c | sort -rn

echo; echo "===== 3. RUNNING SERVERS: healthy? producing? real errors? ====="
for j in $(squeue -u "$USER" -h -t R -o %i); do
  echo "--- $j ---"
  grep -hE "healthy|\[run\]" "slurm-$j.out" 2>/dev/null | tail -2
  log="$SCRATCH/harnesslab/serverlogs/${j}_8001.log"
  [ -f "$log" ] && grep -m1 -E "torchvision::nms|_vllm_fa|illegal memory|Disk quota|CUDA error|Traceback|ValueError" "$log" | sed 's/^/   REAL-ERR> /'
done

echo; echo "===== 4. ALL STORES + census total ====="
tot=0
for d in "$SCRATCH"/harnesslab/*/rollouts_*; do
  [ -f "$d/rollouts.jsonl" ] || continue
  n=$(wc -l < "$d/rollouts.jsonl")
  case "$d" in *mvp_grid/*|*mvp_thin*) tot=$((tot+n));; esac
  printf "  %9d  %s\n" "$n" "${d#"$SCRATCH"/harnesslab/}"
done | sort -rn
echo "  --------- census total (mvp_grid + thin): $tot ---------"

echo; echo "===== 5. MODELS with data ====="
ls -d "$SCRATCH"/harnesslab/*/rollouts_* 2>/dev/null \
  | sed -E 's#.*/rollouts_##' | sed -E 's/_(hotpotqa|musique|gsm8k|math)$//' \
  | sort | uniq -c

echo; echo "===== 6. RECENT PROBE VERDICTS (last 8h) ====="
for j in $(sacct -u "$USER" --starttime now-8hours -X -n -o JobID,JobName 2>/dev/null | awk '/probe/{print $1}'); do
  m=$(grep -m1 '\[serve\]' "slurm-$j.out" 2>/dev/null | awk '{print $2}')
  v=$(grep -hoE "Action: [A-Za-z]+\[|Answer:|<\|call\|>|Chinese|ValueError:|FATAL|healthy" "slurm-$j.out" 2>/dev/null | sort -u | tr '\n' ' ')
  echo "  probe $j  ${m:-?}  :: ${v:-<no verdict — still loading or died>}"
done

echo; echo "===== 3k cap on this clone (should say 3000) ====="
grep -m1 "n_tasks" configs/experiments/mvp_grid.yaml
