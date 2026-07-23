#!/bin/bash
# JUPITER environment bootstrap (§7) — LOGIN NODE, idempotent, run from repo root.
#   bash scripts/hpc/setup_env.sh
# Builds: .venv with harnesslab[data] + vLLM (wheel if a CUDA aarch64 wheel
# resolves, else source build per the SDLAML guide — expect ~1h for the build).
set -euo pipefail

module load Stages/2025 GCC Python CUDA 2>/dev/null \
  || echo "[setup] WARNING: module load failed — check 'module avail' names and rerun"
python3 --version

if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -U pip
pip install -e ".[data]"

if ! python -c "import vllm" 2>/dev/null; then
  echo "[setup] installing vLLM (wheel attempt first)"
  if ! pip install vllm; then
    echo "[setup] no usable wheel — building vLLM from source (AArch64, CUDA)"
    mkdir -p vendor
    [ -d vendor/vllm ] || git clone https://github.com/vllm-project/vllm vendor/vllm
    pushd vendor/vllm
    python use_existing_torch.py 2>/dev/null || true
    pip install -r requirements/build.txt 2>/dev/null || pip install -r requirements-build.txt
    VLLM_TARGET_DEVICE=cuda pip install -e . --no-build-isolation
    popd
  fi
fi
python - <<'PY'
import vllm, harnesslab, sympy, polars
print(f"[setup] OK  vllm={vllm.__version__}  harnesslab={harnesslab.__version__}")
PY
echo "[setup] next: export HF_TOKEN, then bash scripts/hpc/prefetch_models.sh --tier G"
