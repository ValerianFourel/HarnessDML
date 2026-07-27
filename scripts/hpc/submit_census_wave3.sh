#!/bin/bash
# Wave-3 census: the three giants, gated 2026-07-27 (configs/gates.yaml) —
# qwen_3_5_122b, llama_4_scout, kimi_linear_48b. All four bands landed inside
# [0.15, 0.85] for all three, so nothing is dropped and nothing goes thin.
#
#   bash scripts/hpc/submit_census_wave3.sh              # all four bands
#   bash scripts/hpc/submit_census_wave3.sh math gsm8k   # cheapest bands only
#
# COST — read before running all four. These serve with --enforce-eager (the
# registry sets it; they will not run otherwise), so ~2-3x slower than wave 1/2
# and chains are sized ~2x. Rollouts per model:
#     math      41,920     musique   386,720
#     gsm8k    211,040     hotpotqa  480,000
# All four bands x 3 models is ~3.36M rollouts — larger than everything
# collected so far (2.78M) and the dominant cost of "census everything".
# math+gsm8k first is ~759k and answers the within-family scale question at a
# fifth of the price; hotpotqa is half the bill on its own.
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh
GRID=configs/experiments/mvp_grid.yaml
BANDS=("$@"); [ ${#BANDS[@]} -gt 0 ] || BANDS=(math gsm8k musique hotpotqa)

# links per band, sized from wave-1 throughput x ~2 for eager serving
links_for() { case "$1" in math) echo 2;; gsm8k) echo 6;; musique) echo 8;; hotpotqa) echo 10;; *) echo 0;; esac; }

chain() {  # chain <n_links> <model> <bench>
  local n=$1 model=$2 bench=$3 dep="" id
  for _ in $(seq 1 "$n"); do
    id=$(EXP="$GRID" MODEL_ID="$model" BENCH="$bench" \
         sbatch --parsable --job-name "hl-$model-$bench" \
                ${dep:+--dependency=afterany:$dep} slurm/run_experiment.sbatch)
    dep=$id
  done
  echo "[wave3] $model x $bench: $n-link chain, tail job $dep"
}

for band in "${BANDS[@]}"; do
  n=$(links_for "$band")
  [ "$n" -gt 0 ] || { echo "[wave3] unknown band '$band' — skipped"; continue; }
  for model in qwen_3_5_122b llama_4_scout kimi_linear_48b; do
    chain "$n" "$model" "$band"
  done
done

squeue -u "$USER" -o "%.11i %.8T %.24j %.9M %R" | tail -20
echo "[wave3] submitted bands: ${BANDS[*]}. Monitor: bash scripts/hpc/overview.sh"

# NOT here:
#   minimax_m2_5      — probe 1048805 came back healthy but with NO "Action:" line;
#                       confirm textual protocol delivery before piloting.
#   deepseek_v4_flash — BLOCKED, UE8M0 fp8 needs CUDA >= 12.8 (module stack is 12.x).
#   llama_3_1_8b      — bridge arm only (arms/bridge_coupled.yaml), not the grid.
