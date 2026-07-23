#!/bin/bash
# Serve MODEL_ID and dump raw chat-completion responses for the instrument's
# BARE and T prompts (scripts/hpc/probe_gptoss.py). Diagnostic only — no
# stores, no results/ artifacts; everything lands in the job log.
#
#   MODEL_ID=gpt_oss_20b sbatch slurm/probe.sbatch
#
#SBATCH --partition=booster
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --time=01:00:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

: "${MODEL_ID:=gpt_oss_20b}"
source scripts/hpc/env.sh
export HF_HOME=${HF_HOME:-$SCRATCH/hf}
export HF_HUB_OFFLINE=1

bash scripts/hpc/serve_node.sh "$MODEL_ID"
source "$SCRATCH/harnesslab/serving_${SLURM_JOB_ID}.env"
trap 'pkill -P $$ || true' EXIT

srun --ntasks=1 --overlap python scripts/hpc/probe_gptoss.py "$MODEL_ID"
