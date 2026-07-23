#!/bin/bash
# Optional afterok aggregation (aggregation is light — a login node works too):
#   sbatch --dependency=afterok:<runjob> --export=ALL,ROLLOUTS=...,EXP_ID=... slurm/aggregate.sbatch
#SBATCH --partition=booster
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --time=00:30:00
#SBATCH --output=slurm-agg-%j.out
set -euo pipefail
: "${ROLLOUTS:?}" ; : "${EXP_ID:?}"
source .venv/bin/activate
srun --ntasks=1 python -m harnesslab.cli aggregate --rollouts "$ROLLOUTS" --out "results/$EXP_ID"
python -m harnesslab.cli verify --panel "results/$EXP_ID/panel.parquet"
echo "[aggregate] commit results/$EXP_ID from a LOGIN node (size guard active)"
