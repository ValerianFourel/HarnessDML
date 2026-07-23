"""Repo and scratch-path resolution. $HAL_DATA_DIR always wins."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Scratch root for raw + decrypted traces + parquet cache (never in git)."""
    env = os.environ.get("HAL_DATA_DIR")
    if env:
        return Path(env)
    link = repo_root() / "data"
    if link.exists():
        return link.resolve()
    raise RuntimeError(
        "No data location: set $HAL_DATA_DIR or create the `data` symlink "
        "(ln -sfn $HAL_DATA_DIR data — see README 'HPC bootstrap')."
    )


def results_dir() -> Path:
    return repo_root() / "results"


def schema_dir() -> Path:
    return repo_root() / "schema"


def configs_dir() -> Path:
    return repo_root() / "configs"
