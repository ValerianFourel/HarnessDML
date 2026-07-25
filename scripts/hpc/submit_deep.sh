#!/bin/bash
# Deep-eval submission (§4.4 extension): after the committed task lists are
# EXTENDED (build_tasks.py --extend, superset property) and pushed, resubmit
# every gated grid slice as its own single-bench job. Stores are the same as
# wave 1, so already_done skips the original 16k per slice and only the
# increment runs — resume-by-construction pays for itself here.
#
#   bash scripts/hpc/submit_deep.sh
#
# Sizing at wave-1 throughput (jobs that hit the 11:30 walltime are safe:
# resubmit the same job and it resumes):
#   QA 100->500:       +64k rollouts per (model, bench)   ~3-8 h
#   gsm8k 100->1319:   +195k (qwen census)                ~10-20 h (may need 2 windows)
#   math 100->262:     +26k per model (census)            ~2-6 h
#   thin gsm8k census: +24k (mistral, 4 configs)          ~1-2 h
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh

for B in hotpotqa musique math; do
  EXP=configs/experiments/mvp_grid.yaml MODEL_ID=mistral_small_3_2_24b BENCH=$B \
    sbatch slurm/run_experiment.sbatch
done
for B in hotpotqa musique gsm8k math; do
  EXP=configs/experiments/mvp_grid.yaml MODEL_ID=qwen_3_5_9b BENCH=$B \
    sbatch slurm/run_experiment.sbatch
done
EXP=configs/experiments/mvp_thin_gsm8k.yaml MODEL_ID=mistral_small_3_2_24b BENCH=gsm8k \
  sbatch slurm/run_experiment.sbatch
squeue -u "$USER"
