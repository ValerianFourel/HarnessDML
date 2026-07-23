"""Thin wrapper around the `hal-decrypt` CLI (princeton-pli/hal-harness).

We never reimplement the crypto — decryption is delegated to the vendored
CLI, installed per README "HPC bootstrap" step 5 (own venv, --no-deps).
`hal-decrypt` writes decrypted files NEXT TO the input zips; plan directory
layout accordingly (data/encrypted/<benchmark>/ holds zips + decrypted json).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .. import paths


def hal_decrypt_bin() -> Path:
    env = os.environ.get("HAL_DECRYPT_BIN")
    candidate = Path(env) if env else paths.repo_root() / "vendor" / ".hal-venv" / "bin" / "hal-decrypt"
    if not candidate.exists():
        raise FileNotFoundError(
            f"hal-decrypt not found at {candidate}. Install it per README "
            "'HPC bootstrap' step 5, or set $HAL_DECRYPT_BIN."
        )
    return candidate


def decrypt_zip(zip_path: Path, binary: Path | None = None) -> None:
    """Decrypt a single run zip in place (outputs land beside the zip)."""
    binary = binary or hal_decrypt_bin()
    subprocess.run([str(binary), "-F", str(zip_path)], check=True)


def decrypt_dir(directory: Path, binary: Path | None = None) -> list[Path]:
    """Decrypt every zip in `directory`; return the decrypted json files.

    The CLI logs and skips files that fail — compare counts against the
    number of zips and treat any shortfall as a discrepancy to report.
    """
    binary = binary or hal_decrypt_bin()
    subprocess.run([str(binary), "-D", str(directory)], check=True)
    return sorted(p for p in directory.glob("*.json") if p.is_file())


def expected_outputs(zip_path: Path) -> list[Path]:
    """Files hal-decrypt would produce for this zip (member names minus .encrypted)."""
    from zipfile import ZipFile

    with ZipFile(zip_path) as z:
        return [zip_path.parent / n.replace(".encrypted", "") for n in z.namelist()]


def decrypt_missing(directory: Path, binary: Path | None = None) -> tuple[list[Path], int]:
    """Idempotent decrypt: only zips whose outputs are absent. PBKDF2 at 480k
    iterations makes re-decryption slow, so reruns must skip completed work.

    Returns (all decrypted json files present, number of zips decrypted now).
    """
    todo = [z for z in sorted(directory.glob("*.zip"))
            if not all(p.exists() for p in expected_outputs(z))]
    if todo:
        binary = binary or hal_decrypt_bin()  # resolved lazily: no-op needs no CLI
        for z in todo:
            decrypt_zip(z, binary)
    return sorted(p for p in directory.glob("*.json") if p.is_file()), len(todo)
