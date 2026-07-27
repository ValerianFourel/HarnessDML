#!/bin/bash
# Census deep eval (§4.4 extension, ADR 19/20): FULL benchmark coverage on
# every gated slice — hotpotqa 7405, musique 2417, gsm8k 1319, math 262.
#
# A census slice is too big for one walltime window (hotpotqa = ~1.18M
# rollouts ≈ 60-110 h on one node) and a store must have ONE writer, so each
# slice runs as a CHAIN of dependent jobs (afterany): every link resumes the
# store where the previous one stopped; finished links no-op instantly.
# All 8 chains run in parallel on separate nodes → wall-clock ≈ 3-5 days,
# ~250-300 node-hours total, zero babysitting.
#
#   bash scripts/hpc/submit_census.sh
#
# PREREQ: the extended task lists are committed and pulled (build_tasks.py
# --extend to the full pools). Chain lengths are sized from wave-1
# throughput + 30% margin; a chain that finishes early just no-ops its tail.
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh

chain() {  # chain <n_links> <exp> <model> <bench>
  local n=$1 exp=$2 model=$3 bench=$4 dep="" id
  for _ in $(seq 1 "$n"); do
    id=$(EXP="$exp" MODEL_ID="$model" BENCH="$bench" \
         sbatch --parsable --job-name "hl-$model-$bench" \
                ${dep:+--dependency=afterany:$dep} slurm/run_experiment.sbatch)
    dep=$id
  done
  echo "[census] $model x $bench: $n-link chain, tail job $dep"
}

GRID=configs/experiments/mvp_grid.yaml
chain 12 "$GRID" mistral_small_3_2_24b hotpotqa   # ~1.18M rollouts
chain  6 "$GRID" mistral_small_3_2_24b musique    # ~387k
chain  2 "$GRID" mistral_small_3_2_24b math       # ~42k
chain  7 "$GRID" qwen_3_5_9b hotpotqa             # ~1.18M (qwen is faster)
chain  4 "$GRID" qwen_3_5_9b musique              # ~387k
chain  2 "$GRID" qwen_3_5_9b gsm8k                # ~211k
chain  1 "$GRID" qwen_3_5_9b math                 # ~42k
chain  1 configs/experiments/mvp_thin_gsm8k.yaml mistral_small_3_2_24b gsm8k  # thin census ~26k
squeue -u "$USER"
