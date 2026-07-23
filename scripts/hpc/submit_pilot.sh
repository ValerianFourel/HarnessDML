#!/bin/bash
# Submit the Phase-4 pilot: (one Tier F + one Tier G) x all four bands (§9).
# Doubles as the difficulty-gate measurement. Review, then run on a login node:
#   bash scripts/hpc/submit_pilot.sh
set -euo pipefail
EXP=configs/experiments/pilot.yaml
BENCHES=hotpotqa,musique,gsm8k,math   # one job per model, benches sequential on-node
# Env-prefix, NOT --export=...,BENCH=a,b,c — sbatch splits --export on commas,
# so a comma list silently truncates to its first entry (pilot job 1029741
# ran hotpotqa only). sbatch propagates the submission env by default.
for MODEL_ID in gpt_oss_120b gpt_oss_20b; do   # ungated pair — no access requests needed
  echo "EXP=$EXP MODEL_ID=$MODEL_ID BENCH=$BENCHES sbatch slurm/run_experiment.sbatch"
  EXP=$EXP MODEL_ID=$MODEL_ID BENCH=$BENCHES sbatch slurm/run_experiment.sbatch
done
squeue -u "$USER"
