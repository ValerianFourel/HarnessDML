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

read -r HF_ID MODE REVISION FAMILY <<<"$(python - "$MODEL_ID" <<'PY'
import sys
from harnesslab.experiment import load_registry
m = load_registry()[sys.argv[1]]
print(m["hf_id"], m["serving_mode"], m.get("revision") or "main", m.get("family", "?"))
PY
)"
echo "[serve] $MODEL_ID -> $HF_ID ($MODE, rev ${REVISION:0:12})"

# gpt-oss + cold harmony vocab cache = healthy servers whose every request
# 500s (offline nodes can't download it — run 1029055). Fail fast instead.
if [ "$FAMILY" = "gpt-oss" ] && ! ls "${TIKTOKEN_RS_CACHE_DIR:-/nonexistent}"/* >/dev/null 2>&1; then
  echo "[serve] FATAL: harmony vocab cache empty (TIKTOKEN_RS_CACHE_DIR=${TIKTOKEN_RS_CACHE_DIR:-unset})"
  echo "[serve] warm it on a LOGIN node first (env.sh sets the cache dir):"
  echo "[serve]   python -c 'from openai_harmony import load_harmony_encoding; load_harmony_encoding(\"HarmonyGptOss\")'"
  exit 5
fi

START_TS=$(date +%s)
PORTS=()
if [ "$MODE" = "one_node_tp4" ]; then
  PORTS=(8001)
  vllm serve "$HF_ID" --revision "$REVISION" --tensor-parallel-size 4 \
    --port 8001 --max-model-len "$MAXLEN" --seed 0 ${EXTRA_VLLM_ARGS:-} \
    >"$LOGDIR/${SLURM_JOB_ID:-$$}_8001.log" 2>&1 &
elif [ "$MODE" = "one_gpu" ]; then
  for i in 0 1 2 3; do
    port=$((8001 + i))
    PORTS+=("$port")
    CUDA_VISIBLE_DEVICES=$i vllm serve "$HF_ID" --revision "$REVISION" \
      --port "$port" --max-model-len "$MAXLEN" --seed 0 ${EXTRA_VLLM_ARGS:-} \
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
