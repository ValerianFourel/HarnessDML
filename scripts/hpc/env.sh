#!/bin/bash
# Source me in EVERY shell — login or batch — before touching the venv:
#
#   source scripts/hpc/env.sh
#
# The venv's python links against the Python module's libpython; without
# `module load` in the current shell, python dies with
# "error while loading shared libraries: libpython3.12.so.1.0".
# Batch jobs must source this too (slurm/*.sbatch do) — --export=ALL only
# copies the submitting shell's environment, it does not load modules.
module load Stages/2025 GCC Python CUDA 2>/dev/null \
  || echo "[env] WARNING: module load failed — run 'module spider Python' and adjust this file"
_HL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$_HL_ROOT/.venv/bin/activate"

# JUPITER: $SCRATCH exists only after `jutil env activate -p <project>`; fall
# back to the per-project variable ($SCRATCH_<project>) so scripts and batch
# jobs never see it unset. ($FSCRATCH/ExaFLASH is faster but 30-day retention
# + strict quota — opt in via `export SCRATCH=$FSCRATCH_<project>` if wanted.)
if [ -z "${SCRATCH:-}" ]; then
  _hl_sc_var="$(env | sed -n 's/^\(SCRATCH_[A-Za-z0-9_]*\)=.*/\1/p' | head -1 || true)"
  if [ -n "${_hl_sc_var:-}" ]; then
    export SCRATCH="${!_hl_sc_var}"
    echo "[env] SCRATCH=$SCRATCH (from \$${_hl_sc_var})"
  else
    echo "[env] WARNING: \$SCRATCH unset — run 'jutil env activate -p <project>'" \
         "(list projects: 'jutil user projects') or export SCRATCH manually"
  fi
fi

# Compile/JIT caches must NOT live in $HOME (tiny quota on JUPITER):
# torch-inductor, triton, vLLM, and DeepGEMM's nvcc JIT filled it during
# concurrent serves — 'Disk quota exceeded' killed qwen-122b/27b probes and
# 'NVCC compilation failed' (DeepGEMM JIT unable to write) killed the FP8
# MoE probes (jobs 1034966/67, 1035023/24). SCRATCH has room; caches rebuild.
if [ -n "${SCRATCH:-}" ]; then
  export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$SCRATCH/cache}"
  export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-$SCRATCH/cache/triton}"
  export TORCHINDUCTOR_CACHE_DIR="${TORCHINDUCTOR_CACHE_DIR:-$SCRATCH/cache/torchinductor}"
  export VLLM_CACHE_ROOT="${VLLM_CACHE_ROOT:-$SCRATCH/cache/vllm}"
  export DG_JIT_CACHE_DIR="${DG_JIT_CACHE_DIR:-$SCRATCH/cache/deepgemm}"
  export DG_CACHE_DIR="${DG_CACHE_DIR:-$SCRATCH/cache/deepgemm}"   # older DeepGEMM name
  # pip/uv too: ~/.cache/pip alone reached 15 GB and pushed $HOME past its
  # 20 GB soft quota — which silently killed EVERY batch job at startup for
  # ~24 h (0-byte logs, exit 1 in seconds; jobs 1042417-1042853)
  export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$SCRATCH/cache/pip}"
  export UV_CACHE_DIR="${UV_CACHE_DIR:-$SCRATCH/cache/uv}"
  mkdir -p "$XDG_CACHE_HOME" "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" \
           "$VLLM_CACHE_ROOT" "$DG_JIT_CACHE_DIR" 2>/dev/null || true
fi

# gpt-oss serving: vLLM renders chats through openai_harmony, which needs the
# o200k_base tiktoken vocab. Its downloader fetches it on FIRST REQUEST (not
# at load — servers come up healthy, then every /chat/completions 500s: run
# 1029055) and can't reach the Azure blob from JUPITER even on login nodes
# (run 1029364). The vocab is therefore VENDORED in-repo, sha256-pinned to
# harmony's own expected hash; this env var makes harmony read it from disk
# and never touch the network.
export TIKTOKEN_ENCODINGS_BASE="${TIKTOKEN_ENCODINGS_BASE:-$_HL_ROOT/assets/harmony-vocab}"
