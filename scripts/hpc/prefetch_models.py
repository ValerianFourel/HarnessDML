"""Prefetch model weights to $SCRATCH and pin revision SHAs (§6/§7).

LOGIN NODE ONLY (internet). Compute jobs run with HF_HUB_OFFLINE=1 against
the same HF_HOME cache. Pinned SHAs go to configs/model_revisions.lock.yaml
(merged into the registry by load_registry — models.yaml comments stay
intact). Gated/missing entries are reported with the action needed — never
silently substituted (§6).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

from harnesslab.experiment import load_registry

LOCK = Path(__file__).resolve().parents[2] / "configs" / "model_revisions.lock.yaml"


def warm_harmony_cache() -> bool:
    """gpt-oss serving needs openai_harmony's tiktoken vocab, which the
    library downloads on first request — impossible on offline compute nodes
    (run 1029055: healthy servers, every request 500 HarmonyError). Download
    it here instead; TIKTOKEN_RS_CACHE_DIR (env.sh) shares it via $SCRATCH."""
    cache = os.environ.get("TIKTOKEN_RS_CACHE_DIR")
    if not cache:
        cache = f"{os.environ['HF_HOME']}/harmony-vocab"
        os.environ["TIKTOKEN_RS_CACHE_DIR"] = cache
    Path(cache).mkdir(parents=True, exist_ok=True)
    try:
        from openai_harmony import load_harmony_encoding

        load_harmony_encoding("HarmonyGptOss")
    except Exception as exc:  # noqa: BLE001
        print(f"[prefetch] harmony vocab warm-up failed: {exc}", file=sys.stderr)
        return False
    n = sum(1 for _ in Path(cache).iterdir())
    print(f"[prefetch] harmony vocab cached -> {cache} ({n} file(s))")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier", nargs="+", default=["F", "G", "B"],
                    help="tiers to prefetch (S is out of MVP scope)")
    ap.add_argument("--model-id", nargs="*", default=None, help="explicit registry keys")
    ap.add_argument("--dry-run", action="store_true", help="resolve + pin only, no download")
    args = ap.parse_args()

    if not os.environ.get("HF_HOME"):
        scratch = os.environ.get("SCRATCH")
        if not scratch:
            print("[prefetch] set HF_HOME or SCRATCH first", file=sys.stderr)
            return 2
        os.environ["HF_HOME"] = f"{scratch}/hf"
    print(f"[prefetch] HF_HOME={os.environ['HF_HOME']}")

    from huggingface_hub import model_info, snapshot_download

    registry = load_registry()
    wanted = {
        mid: m for mid, m in registry.items()
        if (args.model_id and mid in args.model_id)
        or (not args.model_id and m["tier"] in args.tier and m.get("enabled", True))
    }

    lock: dict = yaml.safe_load(LOCK.read_text()) if LOCK.exists() else {}
    lock = lock or {}
    failures = []
    if not args.dry_run:
        harmony_ok = warm_harmony_cache()
        if not harmony_ok and any(m.get("family") == "gpt-oss" for m in wanted.values()):
            failures.append("harmony-vocab")
    for mid, m in wanted.items():
        hf_id = m["hf_id"]
        try:
            info = model_info(hf_id)
            sha = info.sha
        except Exception as exc:  # noqa: BLE001
            failures.append(mid)
            verify = " (verify entry — resolve the correct hf_id)" if m.get("verify") else ""
            print(f"[prefetch] {mid}: CANNOT RESOLVE {hf_id!r}: {exc}{verify}\n"
                  f"           if gated: request access on the hub, set HF_TOKEN, rerun")
            continue
        lock[mid] = sha
        print(f"[prefetch] {mid}: {hf_id} @ {sha[:12]}", end="")
        if args.dry_run:
            print("  (dry-run)")
            continue
        snapshot_download(hf_id, revision=sha)
        print("  downloaded")

    LOCK.write_text(
        "# pinned by scripts/hpc/prefetch_models.py — commit this file\n"
        + yaml.safe_dump(lock, sort_keys=True)
    )
    print(f"[prefetch] pinned {len(lock)} revisions -> {LOCK}")
    if failures:
        print(f"[prefetch] UNRESOLVED: {failures} — fix hf_ids in configs/models.yaml")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
