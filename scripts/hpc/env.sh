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
