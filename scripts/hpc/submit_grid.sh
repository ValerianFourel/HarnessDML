#!/bin/bash
# Submit the Phase-5 MVP grid: gated (model, band) matrix from the Phase-4
# pilot (ADR 18). Login node, AFTER the Phase-4 STOP is approved:
#
#   bash scripts/hpc/submit_grid.sh            # full grid + thin arm
#   bash scripts/hpc/submit_grid.sh topup      # K=10 headline seeds (run AFTER grid green)
#
# One job per model; benches run sequentially on the served model. Per-slice
# stores make the jobs concurrency-safe. Budget: 7 full slices x 16k + thin 2k
# + topup 6k ~ 120k rollouts ~ 15-30 node-hours at measured throughput.
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh

if [ "${1:-}" = "topup" ]; then
  # K=10 headline top-up on the Tier-F backbone. SAME store dirs as the grid
  # (exp_id=mvp_grid in the yaml): seeds 0-4 skip as already_done, 5-9 run.
  for B in hotpotqa musique math; do
    EXP=configs/experiments/mvp_headline_topup.yaml MODEL_ID=mistral_small_3_2_24b BENCH=$B \
      sbatch slurm/run_experiment.sbatch
  done
  squeue -u "$USER"
  exit 0
fi

# Full 32-config slices (gated bands only)
EXP=configs/experiments/mvp_grid.yaml MODEL_ID=mistral_small_3_2_24b BENCH=hotpotqa,musique,math \
  sbatch slurm/run_experiment.sbatch
EXP=configs/experiments/mvp_grid.yaml MODEL_ID=qwen_3_5_9b BENCH=hotpotqa,musique,gsm8k,math \
  sbatch slurm/run_experiment.sbatch
# Saturation thin arm: mistral x gsm8k, 4 headline configs (ADR 18)
EXP=configs/experiments/mvp_thin_gsm8k.yaml MODEL_ID=mistral_small_3_2_24b BENCH=gsm8k \
  sbatch slurm/run_experiment.sbatch
squeue -u "$USER"
