"""Run manifests (§1.4): every job writes one; every panel row resolves to one."""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _git_state(root: Path) -> dict:
    try:
        def g(*args: str) -> str:
            return subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True, check=True
            ).stdout.strip()

        return {"sha": g("rev-parse", "HEAD"), "dirty": bool(g("status", "--porcelain"))}
    except Exception:  # noqa: BLE001
        # Compute nodes may lack the git binary (smoke 1029480 wrote
        # sha=unknown): read .git/HEAD directly. Dirtiness is unverifiable
        # without git — record None, never a fabricated False.
        try:
            git_dir = root / ".git"
            head = (git_dir / "HEAD").read_text().strip()
            if head.startswith("ref:"):
                ref = head.split(None, 1)[1]
                ref_file = git_dir / ref
                if ref_file.exists():
                    sha = ref_file.read_text().strip()
                else:
                    sha = next(
                        line.split()[0]
                        for line in (git_dir / "packed-refs").read_text().splitlines()
                        if line.split()[-1:] == [ref]
                    )
            else:
                sha = head  # detached HEAD
            return {"sha": sha, "dirty": None}
        except Exception:  # noqa: BLE001 — non-repo contexts still get a manifest
            return {"sha": "unknown", "dirty": None}


def write_manifest(
    out_dir: Path | str,
    *,
    exp_id: str,
    exp_config: dict,
    model: dict,
    sampling: dict,
    template_hashes: dict,
    client_info: dict,
    extra: dict | None = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": _git_state(root),
        "exp_id": exp_id,
        "exp_config_sha256": hashlib.sha256(
            json.dumps(exp_config, sort_keys=True, default=str).encode()
        ).hexdigest(),
        "model": model,  # hf repo + revision SHA once pinned (§1.4)
        "sampling": sampling,
        "component_template_hashes": template_hashes,
        "client": client_info,
        "node": socket.gethostname(),
        "extra": extra or {},
    }
    path = out_dir / f"manifest_{exp_id}.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return path
