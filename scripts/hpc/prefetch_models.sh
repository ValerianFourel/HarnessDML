#!/bin/bash
# Thin wrapper (§7 names this file): login node only.
#   export HF_TOKEN=hf_...   # needed for gated models (Llama, Gemma)
#   bash scripts/hpc/prefetch_models.sh --tier F G B
set -euo pipefail
source .venv/bin/activate
exec python scripts/hpc/prefetch_models.py "$@"
