"""Hugging Face I/O for `agent-evals/hal_traces`.

NETWORK REQUIRED — call these from a login/JupyterHub node only
(notebooks 00/01), never from offline compute notebooks.

Repo facts (verified 2026-07-23): public, ungated, flat layout, 380 zips,
113.1 GB. One encrypted zip per run. Most files are named
``<benchmark>_<run>_UPLOAD.zip``, but Online Mind2Web runs are scaffold-first
with no benchmark prefix (``browser-use_*``, ``seeact_*``), and CoLBench runs
(not among the paper's 9 benchmarks) are present too. Filename buckets are
inventory bookkeeping only — benchmark identity is resolved from the decrypted
trace config during ETL, never from filenames.
"""

from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

from .. import paths

REPO_ID = "agent-evals/hal_traces"

# Filename-prefix buckets; longest match wins.
KNOWN_BENCHMARKS = [
    "assistantbench",
    "colbench_backend_programming",
    "colbench_frontend_design",
    "corebench_hard",
    "gaia",
    "scicode",
    "scienceagentbench",
    "swebench_verified_mini",
    "taubench_airline",
    "usaco",
    "browser-use",
    "seeact",
]

# Scaffold-first buckets and what they presumably contain (display only).
PRESUMED_BENCHMARK = {
    "browser-use": "online_mind2web",
    "seeact": "online_mind2web",
}

ASK_THRESHOLD_GB = 5.0  # CLAUDE.md guardrail 6


def bucket_for(filename: str) -> str:
    matches = [b for b in KNOWN_BENCHMARKS if filename.startswith(b + "_")]
    return max(matches, key=len) if matches else "UNRECOGNIZED"


def list_zips(api=None) -> list[tuple[str, int]]:
    """[(path, size_bytes)] for every zip in the dataset repo."""
    from huggingface_hub import HfApi

    api = api or HfApi(token=os.environ.get("HF_TOKEN"))
    return [
        (entry.path, entry.size)
        for entry in api.list_repo_tree(REPO_ID, repo_type="dataset", recursive=True)
        if entry.path.endswith(".zip")
    ]


def inventory(files: list[tuple[str, int]] | None = None) -> list[dict]:
    """Per-bucket rows: counts, sizes, and the exact member file list."""
    files = files if files is not None else list_zips()
    buckets: dict[str, list[tuple[str, int]]] = {}
    for path, size in files:
        buckets.setdefault(bucket_for(path), []).append((path, size))

    rows = []
    for bench, members in sorted(buckets.items()):
        sizes = [s for _, s in members]
        rows.append(
            {
                "benchmark": bench,
                "presumed": PRESUMED_BENCHMARK.get(bench, bench),
                "n_files": len(members),
                "total_gb": round(sum(sizes) / 1e9, 2),
                "min_mb": round(min(sizes) / 1e6, 1),
                "median_mb": round(statistics.median(sizes) / 1e6, 1),
                "max_mb": round(max(sizes) / 1e6, 1),
                "files": [{"path": p, "size": s} for p, s in sorted(members)],
            }
        )
    return rows


def write_inventory_reports(rows: list[dict] | None = None, reports_dir: Path | None = None) -> Path:
    """Write reports/hf_inventory.{md,json}; return the md path."""
    rows = rows if rows is not None else inventory()
    reports_dir = reports_dir or paths.repo_root() / "reports"
    reports_dir.mkdir(exist_ok=True)

    (reports_dir / "hf_inventory.json").write_text(json.dumps(rows, indent=2))

    n = sum(r["n_files"] for r in rows)
    gb = sum(r["total_gb"] for r in rows)
    lines = [
        f"# HF inventory: `{REPO_ID}`",
        "",
        f"{n} zip files, {gb:.1f} GB total.",
        "",
        "| bucket | presumed benchmark | files | total GB | min MB | median MB | max MB |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['benchmark']} | {r['presumed']} | {r['n_files']} | {r['total_gb']} "
            f"| {r['min_mb']} | {r['median_mb']} | {r['max_mb']} |"
        )
    md = reports_dir / "hf_inventory.md"
    md.write_text("\n".join(lines) + "\n")
    return md


def slice_filenames(benchmark: str, files: list[tuple[str, int]] | None = None) -> list[str]:
    files = files if files is not None else list_zips()
    names = [p for p, _ in files if bucket_for(p) == benchmark]
    if not names:
        known = ", ".join(KNOWN_BENCHMARKS)
        raise ValueError(f"no files bucketed as {benchmark!r}; known buckets: {known}")
    return sorted(names)


def download_slice(
    benchmark: str,
    dest: Path | None = None,
    token: str | None = None,
    confirmed: bool = False,
) -> list[Path]:
    """Resumable download of one benchmark slice to scratch.

    Refuses slices above the 5 GB guardrail unless ``confirmed=True`` —
    which is only ever set after the user has explicitly approved the size.
    """
    from huggingface_hub import snapshot_download

    files = list_zips()
    names = slice_filenames(benchmark, files)
    total_gb = sum(s for p, s in files if p in set(names)) / 1e9
    if total_gb > ASK_THRESHOLD_GB and not confirmed:
        raise RuntimeError(
            f"slice {benchmark!r} is {total_gb:.2f} GB (> {ASK_THRESHOLD_GB} GB). "
            "Ask before downloading (CLAUDE.md guardrail 6); rerun with confirmed=True "
            "only after explicit approval."
        )

    dest = dest or paths.data_dir() / "encrypted" / benchmark
    dest.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        local_dir=dest,
        allow_patterns=names,
        token=token or os.environ.get("HF_TOKEN"),
    )
    return sorted(dest.glob("*.zip"))


if __name__ == "__main__":
    md = write_inventory_reports()
    print(md.read_text())
