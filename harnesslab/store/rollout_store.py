"""Append-only JSONL rollout store keyed by hash(cell, task_id, seed).

Resume by construction (§7): completed keys are skipped; re-submission of
finished work is a no-op. A partially-written (corrupt) trailing line — the
signature of a killed job — is tolerated on load: the line is ignored and
that rollout simply re-runs (§8.6).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Iterator


def make_rollout_key(cell: dict, task_id: str, seed: int) -> str:
    payload = json.dumps({"cell": cell, "task_id": task_id, "seed": seed}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class RolloutStore:
    def __init__(self, directory: Path | str):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "rollouts.jsonl"
        self.n_corrupt = 0
        self._done: set[str] = set()
        self._load()

    def _load(self) -> None:
        self._needs_newline = False
        if not self.path.exists():
            return
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    self._done.add(rec["rollout_key"])
                except (json.JSONDecodeError, KeyError):
                    self.n_corrupt += 1  # ignored; that rollout re-runs
        with open(self.path, "rb") as fb:  # unterminated tail (killed mid-write)?
            fb.seek(0, os.SEEK_END)
            if fb.tell() > 0:
                fb.seek(-1, os.SEEK_END)
                self._needs_newline = fb.read(1) != b"\n"

    def is_done(self, rollout_key: str) -> bool:
        return rollout_key in self._done

    def __len__(self) -> int:
        return len(self._done)

    def append(self, record: dict) -> None:
        key = record["rollout_key"]
        if key in self._done:
            return  # idempotent
        with open(self.path, "a", encoding="utf-8") as f:
            if self._needs_newline:  # never glue onto a corrupt tail
                f.write("\n")
                self._needs_newline = False
            f.write(json.dumps(record, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self._done.add(key)

    def records(self) -> Iterator[dict]:
        if not self.path.exists():
            return
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
