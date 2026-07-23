"""Run manifests — mandatory provenance for every HPC artifact push.

`results/manifests/<run_id>.json` records: code git SHA (+dirty flag), config
hash, seeds, package versions + full-freeze digest, hostname, timestamps,
input slice checksums, rollout counts. Every artifact filename embeds run_id.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import socket
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .. import paths

KEY_PACKAGES = [
    "doubleml",
    "lightgbm",
    "scikit-learn",
    "statsmodels",
    "polars",
    "pyarrow",
    "numpy",
    "scipy",
    "huggingface-hub",
    "cryptography",
]


def new_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"{now:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"


def file_sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def git_state(root: Path | None = None) -> dict:
    root = root or paths.repo_root()
    def _git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
    return {"sha": _git("rev-parse", "HEAD"), "dirty": bool(_git("status", "--porcelain"))}


def package_versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for name in KEY_PACKAGES:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = None
    return out


def freeze_digest() -> str:
    """sha256 over the full sorted `name==version` list of the environment."""
    entries = sorted(
        f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions()
    )
    return hashlib.sha256("\n".join(entries).encode()).hexdigest()


def write_manifest(
    run_id: str,
    out_dir: Path | None = None,
    config_path: Path | None = None,
    seeds: dict | None = None,
    input_checksums: dict[str, str] | None = None,
    counts: dict[str, int] | None = None,
    extra: dict | None = None,
) -> Path:
    out_dir = out_dir or paths.results_dir() / "manifests"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "git": git_state(),
        "config": (
            {"path": str(config_path), "sha256": file_sha256(Path(config_path))}
            if config_path
            else None
        ),
        "seeds": seeds or {},
        "package_versions": package_versions(),
        "freeze_digest": freeze_digest(),
        "input_checksums": input_checksums or {},
        "counts": counts or {},
        "extra": extra or {},
    }
    out = out_dir / f"{run_id}.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return out
