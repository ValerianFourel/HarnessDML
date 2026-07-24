#!/bin/bash
# Launch vLLM serving for one model on the current node (§7), then wait
# until healthy. one_gpu -> 4 independent servers (ports 8001-8004);
# one_node_tp4 -> one server, TP=4, port 8001.
#
#   bash scripts/hpc/serve_node.sh <model_id>
#
# Writes $SCRATCH/harnesslab/serving_${SLURM_JOB_ID:-$$}.env with
# BASE_URLS + HARNESSLAB_SERVER_START_TS for the client step to source.
# Extra vLLM flags via $EXTRA_VLLM_ARGS; context cap via $MAXLEN (default 16384).
set -euo pipefail

MODEL_ID=${1:?usage: serve_node.sh <model_id>}
export HF_HOME=${HF_HOME:-$SCRATCH/hf}
export HF_HUB_OFFLINE=1
MAXLEN=${MAXLEN:-16384}
LOGDIR=$SCRATCH/harnesslab/serverlogs
mkdir -p "$LOGDIR"

{ read -r HF_ID MODE REVISION FAMILY; read -r MODEL_VLLM_ARGS; } <<<"$(python - "$MODEL_ID" <<'PY'
import sys
from harnesslab.experiment import load_registry
m = load_registry()[sys.argv[1]]
print(m["hf_id"], m["serving_mode"], m.get("revision") or "main", m.get("family", "?"))
print(m.get("extra_vllm_args") or "")
PY
)"
echo "[serve] $MODEL_ID -> $HF_ID ($MODE, rev ${REVISION:0:12})${MODEL_VLLM_ARGS:+ extra: $MODEL_VLLM_ARGS}"

# gpt-oss + missing harmony vocab = healthy servers whose every request 500s
# (harmony can't download it on JUPITER — runs 1029055/1029364). The vocab is
# vendored in-repo and exposed via TIKTOKEN_ENCODINGS_BASE (env.sh); fail
# fast if it's not there instead of serving doomed servers.
if [ "$FAMILY" = "gpt-oss" ] && [ ! -f "${TIKTOKEN_ENCODINGS_BASE:-}/o200k_base.tiktoken" ]; then
  echo "[serve] FATAL: harmony vocab missing (TIKTOKEN_ENCODINGS_BASE=${TIKTOKEN_ENCODINGS_BASE:-unset})"
  echo "[serve] it is vendored in-repo: git pull, then source scripts/hpc/env.sh"
  exit 5
fi

START_TS=$(date +%s)
PORTS=()
# --served-model-name pins the API name to the hf_id: vLLM sometimes
# registers the model under its resolved local snapshot path instead
# (seen on gpt-oss-120b job 1029740), which would 404 every client request.
if [ "$MODE" = "one_node_tp4" ]; then
  PORTS=(8001)
  # --disable-custom-all-reduce: vLLM's custom all-reduce kernel hits
  # "illegal memory access" (custom_all_reduce.cuh:455) on GH200 TP=4 —
  # killed both 120b jobs (1029740/1029939). PYNCCL fallback is stable.
  vllm serve "$HF_ID" --revision "$REVISION" --served-model-name "$HF_ID" \
    --tensor-parallel-size 4 --disable-custom-all-reduce \
    --port 8001 --max-model-len "$MAXLEN" --seed 0 \
    ${MODEL_VLLM_ARGS:-} ${EXTRA_VLLM_ARGS:-} \
    >"$LOGDIR/${SLURM_JOB_ID:-$$}_8001.log" 2>&1 &
elif [ "$MODE" = "one_gpu" ]; then
  for i in 0 1 2 3; do
    port=$((8001 + i))
    PORTS+=("$port")
    CUDA_VISIBLE_DEVICES=$i vllm serve "$HF_ID" --revision "$REVISION" \
      --served-model-name "$HF_ID" \
      --port "$port" --max-model-len "$MAXLEN" --seed 0 \
      ${MODEL_VLLM_ARGS:-} ${EXTRA_VLLM_ARGS:-} \
      >"$LOGDIR/${SLURM_JOB_ID:-$$}_${port}.log" 2>&1 &
  done
else
  echo "[serve] serving_mode=$MODE is out of MVP scope"; exit 3
fi

for port in "${PORTS[@]}"; do
  echo -n "[serve] waiting for :$port "
  for _ in $(seq 1 240); do  # up to 40 min for big model loads
    if curl -sf "http://localhost:$port/health" >/dev/null 2>&1; then
      echo "healthy"; break
    fi
    sleep 10; echo -n "."
  done
  curl -sf "http://localhost:$port/health" >/dev/null || { echo " FAILED"; exit 4; }
done

URLS=$(printf "http://localhost:%s/v1," "${PORTS[@]}")
ENVFILE=$SCRATCH/harnesslab/serving_${SLURM_JOB_ID:-$$}.env
{
  echo "export BASE_URLS=${URLS%,}"
  echo "export HARNESSLAB_SERVER_START_TS=$START_TS"
  echo "export HARNESSLAB_GPU_PER_ROLLOUT=${HARNESSLAB_GPU_PER_ROLLOUT:-4}"
} >"$ENVFILE"
echo "[serve] ready — source $ENVFILE"
