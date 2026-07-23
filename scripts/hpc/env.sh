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

# gpt-oss serving: vLLM renders chats through openai_harmony, which needs the
# o200k_base tiktoken vocab. Its downloader fetches it on FIRST REQUEST (not
# at load — servers come up healthy, then every /chat/completions 500s: run
# 1029055) and can't reach the Azure blob from JUPITER even on login nodes
# (run 1029364). The vocab is therefore VENDORED in-repo, sha256-pinned to
# harmony's own expected hash; this env var makes harmony read it from disk
# and never touch the network.
export TIKTOKEN_ENCODINGS_BASE="${TIKTOKEN_ENCODINGS_BASE:-$_HL_ROOT/assets/harmony-vocab}"
