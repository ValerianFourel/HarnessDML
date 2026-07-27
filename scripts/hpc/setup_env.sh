#!/bin/bash
# JUPITER environment bootstrap (§7) — LOGIN NODE, idempotent, run from repo root.
#   bash scripts/hpc/setup_env.sh
# Builds: .venv with harnesslab[data] + vLLM (wheel if a CUDA aarch64 wheel
# resolves, else source build per the SDLAML guide — expect ~1h for the build).
set -euo pipefail

# Pinned instrument versions (ADR 21). Treat as a matched set — vLLM's compiled
# extensions are ABI-linked to this exact torch; bump all three together and
# re-prefetch, never one alone. The manifest records the served vLLM version, so
# a change here is a logged instrument change, not a silent one.
VLLM_PIN=${VLLM_PIN:-0.25.1}
TORCH_PIN=${TORCH_PIN:-2.11.0}
TORCHVISION_PIN=${TORCHVISION_PIN:-0.26.0}
# huggingface_hub is part of the matched set too (ADR 24): vLLM's CLI imports
# transformers, which imports huggingface_hub.utils — a hub version whose
# internals transformers does not expect breaks `vllm serve` while `import
# vllm` still passes. pyproject only says >=0.30, so pip is free to drift it.
HF_HUB_PIN=${HF_HUB_PIN:-1.25.1}

module load Stages/2025 GCC Python CUDA 2>/dev/null \
  || echo "[setup] WARNING: module load failed — check 'module avail' names and rerun"
python3 --version

if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -U pip
pip install -e ".[data]"

if ! python -c "import vllm" 2>/dev/null; then
  echo "[setup] installing vLLM $VLLM_PIN (wheel attempt first)"
  if ! pip install "vllm==$VLLM_PIN"; then
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

# Pin the torch stack to what vLLM $VLLM_PIN was built against, LAST and with
# --no-deps. vLLM's compiled C extensions (torchvision ops, _vllm_fa2_C/_fa3_C,
# vllm._C) are ABI-linked to a specific torch build; a resolve that bumps torch
# silently breaks ALL of them and every `vllm serve` dies at the 40-min health
# ceiling while a bare `import vllm` still passes (2026-07-26 incident: a stray
# `uv pip install` moved torch 2.11.0 -> 2.13.0 and killed the whole census
# fleet; ADR 21). --no-deps so this reconciliation itself cannot move anything.
echo "[setup] pinning torch stack: torch==$TORCH_PIN (matches vLLM $VLLM_PIN)"
pip install --no-deps --force-reinstall \
  "torch==$TORCH_PIN" "torchvision==$TORCHVISION_PIN" "torchaudio==$TORCH_PIN"
echo "[setup] pinning huggingface_hub==$HF_HUB_PIN (ADR 24)"
pip install --no-deps --force-reinstall "huggingface_hub==$HF_HUB_PIN"

# Verify the SERVE path, not just `import vllm`: the flash-attn C extension
# loads lazily at serve time, so it is the real ABI canary (mirrors the
# fast preflight in serve_node.sh).
python - <<'PY'
import importlib, sys
# the CLI entry point, not a bare `import vllm`: it pulls vllm.config ->
# transformers -> huggingface_hub, the layer ADR 24 broke
importlib.import_module("vllm.entrypoints.cli.main")
ok = False
for m in ("vllm.vllm_flash_attn._vllm_fa2_C", "vllm.vllm_flash_attn._vllm_fa3_C"):
    try:
        importlib.import_module(m); ok = True; break
    except Exception:
        pass
if not ok:
    sys.exit("[setup] FATAL: vLLM compiled extensions won't load — torch ABI "
             "mismatch. Check torch==%s and re-run." % __import__("torch").__version__)
import vllm, harnesslab, torch
print(f"[setup] OK  vllm={vllm.__version__}  torch={torch.__version__}  "
      f"cuda={torch.version.cuda}  harnesslab={harnesslab.__version__}")
PY
echo "[setup] next: export HF_TOKEN, then bash scripts/hpc/prefetch_models.sh --tier G"
