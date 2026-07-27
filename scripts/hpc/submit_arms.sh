#!/bin/bash
# Submit the Phase-5 control arms (§4.1/§4.3/§4.6):
#
#   bash scripts/hpc/submit_arms.sh          # padding, ordering, template, temp0
#   bash scripts/hpc/submit_arms.sh bridge   # the CCI reconciliation pair
#
# ~17k rollouts total (padding 6k + ordering 3k + template 1.5k + temp0 2.4k
# x bands) ≈ 2-5 node-hours across 4 jobs; all on the already-proven mistral.
# DONE and harvested 2026-07-26 — re-running is a no-op (resume skips).
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh

if [ "${1:-}" = "bridge" ]; then
  # §4.2.1 reconciliation: CCI couples submission INSIDE the T block, we
  # decouple it. Both halves must exist on the SAME model and cell set or the
  # comparison has two differences in it — so this submits the coupled arm and
  # its decoupled twin (mvp_grid narrowed to the arm's 100 tasks x 2 seeds).
  # 6,400 rollouts each, ~2-3 node-hours total.
  #
  # Note llama_3_1_8b's pilot: T y=0.000 on QA under the DECOUPLED protocol
  # (hallucinates the Observation, never answers). That is the finding this
  # pair is meant to attribute — instrument or model — so a degenerate coupled
  # arm is an informative result, not a wasted run.
  for half in coupled decoupled; do
    EXP=configs/experiments/arms/bridge_$half.yaml MODEL_ID=llama_3_1_8b BENCH=hotpotqa \
      sbatch --job-name "hl-bridge-$half" slurm/run_experiment.sbatch
  done
  squeue -u "$USER" -o "%.11i %.9T %.24j %.9M %R" | tail -5
  echo "[arms] bridge pair submitted"
  exit 0
fi

EXP=configs/experiments/arms/padding.yaml  MODEL_ID=mistral_small_3_2_24b BENCH=hotpotqa,math \
  sbatch slurm/run_experiment.sbatch
EXP=configs/experiments/arms/ordering.yaml MODEL_ID=mistral_small_3_2_24b BENCH=hotpotqa \
  sbatch slurm/run_experiment.sbatch
EXP=configs/experiments/arms/template.yaml MODEL_ID=mistral_small_3_2_24b BENCH=hotpotqa \
  sbatch slurm/run_experiment.sbatch
EXP=configs/experiments/arms/temp0.yaml    MODEL_ID=mistral_small_3_2_24b BENCH=hotpotqa,math \
  sbatch slurm/run_experiment.sbatch
squeue -u "$USER"
