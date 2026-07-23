"""Results-contract guard (CLAUDE.md guardrail 4).

HPC may push ONLY `results/` and `schema/`, and no single file above 25 MB.
Run by notebooks/05_export_results.ipynb after `git add`, before commit:

    python scripts/check_results_size.py --staged   # validate the git index
    python scripts/check_results_size.py --tree     # scan results/ on disk

Exit code 1 on any violation. No dependencies beyond the stdlib, so it runs
in any environment, including a bare cluster python.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 25 * 2**20  # 25 MB
ALLOWED_PREFIXES = ("results/", "schema/")


def violations(entries: list[tuple[str, int]]) -> list[str]:
    """entries: (repo-relative posix path, size in bytes). Pure — unit tested."""
    problems = []
    for path, size in entries:
        if not path.startswith(ALLOWED_PREFIXES):
            problems.append(
                f"{path}: outside {ALLOWED_PREFIXES} — HPC commits results/ and schema/ only"
            )
        if size > MAX_BYTES:
            problems.append(f"{path}: {size / 2**20:.1f} MB > 25 MB limit")
    return problems


def staged_entries(root: Path) -> list[tuple[str, int]]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout
    entries = []
    for name in filter(None, out.split("\0")):
        p = root / name
        entries.append((name, p.stat().st_size if p.is_file() else 0))
    return entries


def tree_entries(root: Path) -> list[tuple[str, int]]:
    entries = []
    for base in ("results", "schema"):
        d = root / base
        if d.exists():
            entries += [
                (p.relative_to(root).as_posix(), p.stat().st_size)
                for p in d.rglob("*") if p.is_file()
            ]
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="validate the git index (default)")
    mode.add_argument("--tree", action="store_true", help="scan results/ + schema/ on disk")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    entries = tree_entries(root) if args.tree else staged_entries(root)
    problems = violations(entries)
    if problems:
        print("RESULTS CONTRACT VIOLATIONS — push blocked:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"results contract OK ({len(entries)} paths checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
