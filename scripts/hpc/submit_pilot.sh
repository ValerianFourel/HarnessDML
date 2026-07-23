#!/bin/bash
# Submit the Phase-4 pilot: (one Tier F + one Tier G) x all four bands (§9).
# Doubles as the difficulty-gate measurement. Review, then run on a login node:
#   bash scripts/hpc/submit_pilot.sh
set -euo pipefail
EXP=configs/experiments/pilot.yaml
for MODEL_ID in gpt_oss_120b gpt_oss_20b; do   # ungated pair — no access requests needed
  for BENCH in hotpotqa musique gsm8k math; do
    echo "sbatch --export=ALL,EXP=$EXP,MODEL_ID=$MODEL_ID,BENCH=$BENCH slurm/run_experiment.sbatch"
    sbatch --export=ALL,EXP=$EXP,MODEL_ID=$MODEL_ID,BENCH=$BENCH slurm/run_experiment.sbatch
  done
done
squeue -u "$USER"
