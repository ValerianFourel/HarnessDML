#!/bin/bash
# Verify the SERVE PATH, not just `import vllm`. Run on a login node after any
# change to the venv, and BEFORE letting queued jobs start into it.
#
#   bash scripts/hpc/check_env.sh
#
# Exit 0 = a `vllm serve` launched now will get past its imports. This walks
# the same chain `.venv/bin/vllm` does, which is where both incidents landed:
# ADR 21 (torch ABI -> compiled extensions) and ADR 24 (huggingface_hub ->
# transformers -> vllm.config). Neither was visible to `import vllm`.
set -uo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh

python - <<'PY'
import importlib, sys

steps = [
    ("huggingface_hub",              "hub"),
    ("huggingface_hub.utils",        "hub.utils (ADR 24: _terminal/_cache_manager)"),
    ("transformers",                 "transformers"),
    ("vllm",                         "vllm core"),
    ("vllm.config",                  "vllm.config (imports transformers)"),
    ("vllm.entrypoints.cli.main",    "vllm CLI entry point — what `vllm serve` runs"),
]
bad = False
for mod, label in steps:
    try:
        importlib.import_module(mod)
        print(f"  ok    {label}")
    except Exception as e:
        bad = True
        print(f"  FAIL  {label}\n        {type(e).__name__}: {e}")
        break

if not bad:
    for m in ("vllm.vllm_flash_attn._vllm_fa2_C", "vllm.vllm_flash_attn._vllm_fa3_C"):
        try:
            importlib.import_module(m)
            print(f"  ok    {m} (lazy at serve time — the ADR 21 hole)")
            break
        except ImportError as e:
            last = e
    else:
        bad = True
        print(f"  FAIL  flash-attn C extensions\n        {last}")

import huggingface_hub, torch, vllm
try:
    import transformers
    tf = transformers.__version__
except Exception:
    tf = "?"
print(f"\nvllm {vllm.__version__} · torch {torch.__version__} · "
      f"hf_hub {huggingface_hub.__version__} · transformers {tf}")
print("SERVE PATH OK" if not bad else "SERVE PATH BROKEN — do not let jobs start")
sys.exit(1 if bad else 0)
PY
rc=$?
if [ $rc -ne 0 ]; then
  cat <<'EOF'

Fix on the LOGIN node, then re-run this. Pinned set (scripts/hpc/setup_env.sh):
  torch trio : pip install --no-deps --force-reinstall torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0
  hub        : pip install --no-deps --force-reinstall huggingface_hub==$HF_HUB_PIN

NEVER install while jobs are starting: pip unlinks before it relinks, and a
job that imports during that window dies on a half-written package even
though the same import succeeds a second later (ADR 24).
EOF
fi
exit $rc
