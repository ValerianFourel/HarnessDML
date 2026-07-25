#!/bin/bash
# Submit the Phase-5 control arms (§4.1/§4.3/§4.6) — everything except the
# bridge, which waits for llama_3_1_8b's probe + pilot gate:
#
#   bash scripts/hpc/submit_arms.sh
#
# ~17k rollouts total (padding 6k + ordering 3k + template 1.5k + temp0 2.4k
# x bands) ≈ 2-5 node-hours across 4 jobs; all on the already-proven mistral.
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh

EXP=configs/experiments/arms/padding.yaml  MODEL_ID=mistral_small_3_2_24b BENCH=hotpotqa,math \
  sbatch slurm/run_experiment.sbatch
EXP=configs/experiments/arms/ordering.yaml MODEL_ID=mistral_small_3_2_24b BENCH=hotpotqa \
  sbatch slurm/run_experiment.sbatch
EXP=configs/experiments/arms/template.yaml MODEL_ID=mistral_small_3_2_24b BENCH=hotpotqa \
  sbatch slurm/run_experiment.sbatch
EXP=configs/experiments/arms/temp0.yaml    MODEL_ID=mistral_small_3_2_24b BENCH=hotpotqa,math \
  sbatch slurm/run_experiment.sbatch
squeue -u "$USER"
