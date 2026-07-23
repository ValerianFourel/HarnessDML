#!/bin/bash
# Optional escape hatch: run an estimation notebook under Slurm when a
# JupyterHub session can't hold Phase 4. Compute nodes are OFFLINE — data,
# venv, and repo must already exist (README "HPC bootstrap" + notebook 01).
#
#   sbatch --export=ALL,HAL_DATA_DIR=/scratch/$USER/hal_data scripts/slurm_template.sbatch
#
#SBATCH --job-name=halcausal-estimate
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=slurm-%j.out

set -euo pipefail
module load python/3.12 2>/dev/null || true
cd "${SLURM_SUBMIT_DIR:-$PWD}"
source .venv/bin/activate
: "${HAL_DATA_DIR:?export HAL_DATA_DIR before sbatch}"

# Executed copies go to scratch, never into results/ (25 MB guard).
mkdir -p "$HAL_DATA_DIR/nbruns"
papermill notebooks/04_estimate.ipynb \
  "$HAL_DATA_DIR/nbruns/04_estimate_${SLURM_JOB_ID}.ipynb" -k halcausal
