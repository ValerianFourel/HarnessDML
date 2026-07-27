#!/bin/bash
# Wave-2 census: models onboarded AFTER the original mistral/qwen census
# (ADR 16 probe -> pilot -> gate; "census everything" scale decision 2026-07-27).
#
#   bash scripts/hpc/submit_census_wave2.sh
#
# SEPARATE from submit_census.sh on purpose: never re-submit a slice that
# already has a running writer (a single-writer store double-written races).
# Only truly-new (model,bench) slices go here. Resume-safe: re-running no-ops
# finished links. Uses mvp_grid.yaml (n_tasks=3000 -> HotpotQA capped).
#
# Gates (pilot BARE/T y in [0.15,0.85], §4.4):
#   gemma_4_e4b      : musique, gsm8k, math   (+ hotpotqa BARE .178 — floor-marginal, included)
#   gemma_4_26b_a4b  : hotpotqa, musique, gsm8k, math   (all BARE in-band; hotpotqa T .149 weak)
#   qwen_3_6_27b     : hotpotqa, musique, gsm8k, math   (clean, T positive everywhere)
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh
GRID=configs/experiments/mvp_grid.yaml

chain() {  # chain <n_links> <model> <bench>
  local n=$1 model=$2 bench=$3 dep="" id
  for _ in $(seq 1 "$n"); do
    id=$(EXP="$GRID" MODEL_ID="$model" BENCH="$bench" \
         sbatch --parsable --job-name "hl-$model-$bench" \
                ${dep:+--dependency=afterany:$dep} slurm/run_experiment.sbatch)
    dep=$id
  done
  echo "[wave2] $model x $bench: $n-link chain, tail job $dep"
}

# ---- ready now: gated, no running writer ----
chain 5 gemma_4_e4b      hotpotqa    # BARE .178 — floor-marginal (flag in ADR)
chain 4 gemma_4_e4b      musique
chain 3 gemma_4_e4b      gsm8k
chain 1 gemma_4_e4b      math
chain 5 gemma_4_26b_a4b  hotpotqa
chain 4 gemma_4_26b_a4b  musique
chain 3 gemma_4_26b_a4b  gsm8k
chain 1 gemma_4_26b_a4b  math
chain 5 qwen_3_6_27b     hotpotqa
chain 4 qwen_3_6_27b     musique
chain 3 qwen_3_6_27b     gsm8k
chain 1 qwen_3_6_27b     math

squeue -u "$USER" -o "%.11i %.8T %.22j %.9M %R" | tail -20
echo "[wave2] submitted. Monitor: bash scripts/hpc/status.sh"

# ============================ NOT YET — do these later ============================
# ministral_3_3b (gated musique, gsm8k): a single grid job is STILL writing its
#   musique store. Chain it ONLY after that job ends (else two writers race):
#     chain 4 ministral_3_3b musique   # after the single job leaves the queue
#     chain 3 ministral_3_3b gsm8k
#
# Giants (serve eager via registry extra_vllm_args -> ~2-3x slower, so ~2x links).
#   ENABLE per band ONLY after each one's pilot gate lands (1048894 qwen-122b,
#   1048895 scout, 1048896 kimi):
#     chain 10 qwen_3_5_122b  <gated-band>
#     chain 10 llama_4_scout  <gated-band>
#     chain 10 kimi_linear_48b <gated-band>
#
# minimax_m2_5 : confirm it emits an "Action:" line first (probe 1048805 showed
#   only pre-Action reasoning) before piloting.
# deepseek_v4_flash : BLOCKED — UE8M0 fp8 needs CUDA>=12.8; module stack is 12.x
#   (tilelang __nv_cvt_float_to_e8m0 undefined). Needs a newer CUDA module.
# llama_3_1_8b : bridge-arm ONLY (standard-protocol T y=0.000 on QA); not general grid.
