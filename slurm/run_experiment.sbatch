#!/bin/bash
# One model on one full booster node; one OR several benchmarks run
# sequentially against the same servers (comma-separate BENCH):
#
#   sbatch --export=ALL,EXP=configs/experiments/pilot.yaml,MODEL_ID=gpt_oss_20b,BENCH=gsm8k \
#     slurm/run_experiment.sbatch
#   sbatch --export=ALL,EXP=...,MODEL_ID=gpt_oss_20b,BENCH=hotpotqa,musique,gsm8k,math ...
#
# One MODEL_ID per job — a node serves exactly one model (4 replicas or TP=4).
# Rollouts stream to $SCRATCH (never git); aggregate afterwards on a login
# node (or via slurm/aggregate.sbatch with --dependency=afterok:<jobid>).
#
#SBATCH --partition=booster
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --time=11:30:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

: "${EXP:?export EXP=configs/experiments/....yaml}"
: "${MODEL_ID:?export MODEL_ID=<registry key>}"
: "${BENCH:?export BENCH=hotpotqa|musique|gsm8k|math}"

source scripts/hpc/env.sh   # modules + venv — batch nodes self-provision
export HF_HOME=${HF_HOME:-$SCRATCH/hf}
export HF_HUB_OFFLINE=1

bash scripts/hpc/serve_node.sh "$MODEL_ID"
source "$SCRATCH/harnesslab/serving_${SLURM_JOB_ID}.env"
trap 'pkill -P $$ || true' EXIT   # stop the vLLM servers when the job ends

EXP_BASE=$(basename "$EXP" .yaml)
for B in ${BENCH//,/ }; do
  EXP_ID="${EXP_BASE}_${MODEL_ID}_${B}"
  OUT="$SCRATCH/harnesslab/$EXP_BASE/rollouts_${MODEL_ID}_${B}"
  srun --ntasks=1 --overlap python -m harnesslab.cli run \
    --exp "$EXP" \
    --set exp_id="$EXP_ID" \
    --set model_id="$MODEL_ID" \
    --set benchmark="$B" \
    --set tasks_file="configs/tasks/${B}.jsonl" \
    --backend openai \
    --base-url "$BASE_URLS" \
    --out "$OUT"
  python -m harnesslab.cli status --rollouts "$OUT"
  echo "[sbatch] aggregate on a login node:"
  echo "  python -m harnesslab.cli aggregate --rollouts $OUT --out results/$EXP_ID"
done
