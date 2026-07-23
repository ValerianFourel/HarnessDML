"""Phase 1: empirical schema discovery over decrypted HAL trace files.

Walks N decrypted run-level json files and emits:

- ``schema/SCHEMA.md``                    — human report: paths, types, presence
- ``schema/paths.json``                   — full machine-readable stats
- ``schema/field_mapping.suggested.yaml`` — regex-ranked candidates per panel column

Nothing downstream may hardcode a field name: Phase-2 ETL reads a *curated*
``schema/field_mapping.yaml`` derived from this report after local review.

Design notes:
- One file in memory at a time; files above ``max_file_gb`` are skipped and
  listed in the report (no silent truncation).
- Dicts that look like keyed collections (more than ``collapse_key_threshold``
  keys, or ≥80% ID-like keys — weave call ids, task ids) are collapsed to a
  ``{*}`` path segment so stats aggregate per-structure, not per-id. The
  decision is per-instance; a path can appear both named and collapsed in
  pathological files, which the report would surface rather than hide.
- Arrays contribute their first ``array_sample`` elements to stats; true
  lengths are recorded separately. Per-parent presence rates are therefore
  computed over *sampled* container instances.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .. import paths as _paths

_ID_RE = re.compile(r"^(?:[0-9a-fA-F][0-9a-fA-F-]{11,}|\d+|[A-Za-z0-9+/=_-]{24,})$")
_PLAIN_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# Panel-column targets (Phase 2) -> regex over full lowercase path.
CANDIDATE_TARGETS = {
    "success": r"success|resolved|passed|correct|score|accuracy|reward",
    "total_cost_usd": r"cost",
    "prompt_tokens": r"prompt_tokens|input_tokens",
    "completion_tokens": r"completion_tokens|output_tokens",
    "reasoning_tokens": r"reasoning_tokens|thinking",
    "model": r"model",
    "reasoning_effort": r"reasoning_effort|effort|budget|thinking",
    "scaffold": r"agent|scaffold",
    "task_id": r"task_id|instance_id|question_id|problem|task",
    "temperature": r"temperature",
    "wall_clock_s": r"time|duration|latency|elapsed|start|end",
    "termination_reason": r"termination|finish_reason|stop_reason|status",
}

_SCALARS = ("str", "int", "float", "bool", "null")


def _type_name(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):  # before int: bool subclasses int
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, dict):
        return "dict"
    if isinstance(v, list):
        return "list"
    return type(v).__name__


def _short(v, n: int = 60) -> str:
    s = repr(v).replace("\n", " ").replace("|", "\\|")
    return s[: n - 1] + "…" if len(s) > n else s


class _Node:
    __slots__ = ("count", "types", "files", "examples", "list_lens", "coll_keys", "coll_card", "parent")

    def __init__(self, parent: str | None):
        self.count = 0
        self.types: Counter = Counter()
        self.files: set[int] = set()
        self.examples: list[str] = []
        self.list_lens: list[int] = []
        self.coll_keys: list[str] = []
        self.coll_card: list[int] = []
        self.parent = parent


class _Walker:
    def __init__(self, array_sample: int, collapse_key_threshold: int, max_depth: int, max_nodes: int):
        self.array_sample = array_sample
        self.collapse_key_threshold = collapse_key_threshold
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.nodes: dict[str, _Node] = {}
        self.overflowed = 0

    def _node(self, path: str, parent: str | None) -> _Node | None:
        nd = self.nodes.get(path)
        if nd is None:
            if len(self.nodes) >= self.max_nodes:
                self.overflowed += 1
                return None
            nd = self.nodes[path] = _Node(parent)
        return nd

    def visit(self, path: str, value, file_idx: int, depth: int = 0, parent: str | None = None) -> None:
        nd = self._node(path, parent)
        if nd is None:
            return
        nd.count += 1
        nd.files.add(file_idx)
        t = _type_name(value)
        nd.types[t] += 1

        if t in _SCALARS and len(nd.examples) < 3:
            s = _short(value)
            if s not in nd.examples:
                nd.examples.append(s)

        if depth >= self.max_depth:
            return

        if t == "list":
            if len(nd.list_lens) < 500:
                nd.list_lens.append(len(value))
            for item in value[: self.array_sample]:
                self.visit(path + "[]", item, file_idx, depth + 1, path)
        elif t == "dict":
            keys = list(value.keys())
            id_like = sum(1 for k in keys if _ID_RE.match(str(k)))
            collapse = len(keys) > self.collapse_key_threshold or (
                keys and id_like / len(keys) >= 0.8
            )
            if collapse:
                nd.coll_card.append(len(keys))
                for k in keys:
                    if len(nd.coll_keys) >= 5:
                        break
                    if str(k) not in nd.coll_keys:
                        nd.coll_keys.append(str(k))
                for k in keys[: self.array_sample]:
                    self.visit(path + ".{*}", value[k], file_idx, depth + 1, path)
            else:
                for k in keys:
                    seg = str(k) if _PLAIN_KEY_RE.match(str(k)) else json.dumps(str(k))
                    self.visit(f"{path}.{seg}", value[k], file_idx, depth + 1, path)


def _pick_files(files: list[Path], n: int) -> list[Path]:
    """Deterministic spread across the size-sorted list (no RNG, reproducible)."""
    if len(files) <= n:
        return files
    by_size = sorted(files, key=lambda p: p.stat().st_size)
    idx = {round(i * (len(by_size) - 1) / (n - 1)) for i in range(n)}
    return sorted(by_size[i] for i in idx)


def _git_sha() -> str:
    try:
        from ..io.manifest import git_state

        st = git_state()
        return st["sha"] + ("+dirty" if st["dirty"] else "")
    except Exception:
        return "unknown"


def _fmt_lens(lens: list[int]) -> str:
    if not lens:
        return ""
    return f"len {min(lens)}/{int(statistics.median(lens))}/{max(lens)}"


def discover_schema(
    trace_dir: Path | str,
    out_md: Path | str | None = None,
    n_files: int | None = None,
    max_file_gb: float = 2.0,
    array_sample: int = 200,
    collapse_key_threshold: int = 12,
    max_depth: int = 12,
    max_paths_in_md: int = 600,
    max_nodes: int = 20000,
) -> Path:
    """Walk decrypted traces in ``trace_dir``; write SCHEMA.md and friends."""
    trace_dir = Path(trace_dir)
    all_files = sorted(p for p in trace_dir.glob("*.json") if p.is_file())
    if not all_files:
        raise FileNotFoundError(f"no decrypted *.json files in {trace_dir}")

    if n_files is None:
        env = _paths.configs_dir() / "env.yaml"
        cfg = yaml.safe_load(env.read_text()) if env.is_file() else {}
        n_files = int(cfg.get("schema_sample_traces", 40))

    chosen = _pick_files(all_files, n_files)
    skipped: list[tuple[str, str]] = []
    walked: list[str] = []

    walker = _Walker(array_sample, collapse_key_threshold, max_depth, max_nodes)
    for path in chosen:
        gb = path.stat().st_size / 1e9
        if gb > max_file_gb:
            skipped.append((path.name, f"{gb:.2f} GB > max_file_gb={max_file_gb}"))
            continue
        try:
            doc = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            skipped.append((path.name, f"parse failure: {e}"))
            continue
        walker.visit("$", doc, file_idx=len(walked))
        walked.append(path.name)
        del doc

    if not walked:
        raise RuntimeError(
            f"walked 0 of {len(chosen)} files (skipped: {[s for s, _ in skipped]})"
        )

    schema_dir = _paths.schema_dir() if out_md is None else Path(out_md).parent
    schema_dir.mkdir(parents=True, exist_ok=True)
    out_md = Path(out_md) if out_md is not None else schema_dir / "SCHEMA.md"

    nodes = walker.nodes

    def parent_rate(path: str, nd: _Node) -> str:
        if nd.parent is None:
            return ""
        parent = nodes.get(nd.parent)
        if parent is None:
            return ""
        denom = (
            sum(min(x, array_sample) for x in parent.list_lens)
            if path.endswith("[]")
            else parent.types.get("dict", 0)
        )
        return f"{min(nd.count / denom, 1.0):.0%}" if denom else ""

    # machine-readable dump
    dump = {
        path: {
            "count": nd.count,
            "types": dict(nd.types),
            "files": len(nd.files),
            "parent": nd.parent,
            "examples": nd.examples,
            "list_lens": [min(nd.list_lens), int(statistics.median(nd.list_lens)), max(nd.list_lens)]
            if nd.list_lens
            else None,
            "collapsed_key_cardinality": [min(nd.coll_card), max(nd.coll_card)] if nd.coll_card else None,
            "collapsed_key_examples": nd.coll_keys or None,
        }
        for path, nd in sorted(nodes.items())
    }
    (schema_dir / "paths.json").write_text(json.dumps(dump, indent=1))

    # candidate mapping suggestions
    suggestions: dict[str, list[dict]] = {}
    for target, pattern in CANDIDATE_TARGETS.items():
        rx = re.compile(pattern)
        hits = [
            (path, nd)
            for path, nd in nodes.items()
            if rx.search(path.lower()) and set(nd.types) & set(_SCALARS)
        ]
        hits.sort(key=lambda kv: (-len(kv[1].files), -kv[1].count, kv[0]))
        suggestions[target] = [
            {
                "path": path,
                "files": f"{len(nd.files)}/{len(walked)}",
                "types": "|".join(sorted(nd.types)),
                "example": nd.examples[0] if nd.examples else None,
            }
            for path, nd in hits[:8]
        ]
    (schema_dir / "field_mapping.suggested.yaml").write_text(
        "# AUTO-GENERATED candidates per panel column — curate into field_mapping.yaml\n"
        "# after local review. Phase-2 ETL refuses to run from this file directly.\n"
        + yaml.safe_dump(suggestions, sort_keys=True, width=120)
    )

    # human report
    lines = [
        "# Empirical trace schema — `SCHEMA.md`",
        "",
        "**STATUS: UNREVIEWED.** Generated by `halcausal.etl.discover_schema`;",
        "review locally, then curate `schema/field_mapping.yaml`. ETL is blocked",
        "until then (CLAUDE.md, Phase 1).",
        "",
        f"- trace dir: `{trace_dir}`",
        f"- files walked: {len(walked)} of {len(all_files)} present (sample target {n_files})",
        f"- generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')} | code: `{_git_sha()}`",
        f"- collapse threshold: {collapse_key_threshold} keys / 80% id-like; array sample: {array_sample}; max depth: {max_depth}",
    ]
    if walker.overflowed:
        lines.append(f"- **WARNING**: path-space overflow — {walker.overflowed} visits beyond {max_nodes} distinct paths were dropped")
    if skipped:
        lines += ["", "## Skipped files", ""]
        lines += [f"- `{name}` — {why}" for name, why in skipped]

    lines += [
        "",
        "## Walked files",
        "",
        *[f"- `{n}`" for n in walked],
        "",
        "## Paths",
        "",
        "`files%` = share of walked files containing the path; `parent%` = presence",
        "per (sampled) parent-container instance. `{*}` = collapsed keyed collection;",
        "`[]` = array element.",
        "",
        "| path | types | n | files% | parent% | container | examples |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    shown = 0
    for path, nd in sorted(nodes.items()):
        if shown >= max_paths_in_md:
            break
        shown += 1
        container = _fmt_lens(nd.list_lens)
        if nd.coll_card:
            keys = ", ".join(nd.coll_keys[:3])
            container = (container + " " if container else "") + \
                f"keys {min(nd.coll_card)}–{max(nd.coll_card)} (e.g. {_short(keys, 40)})"
        lines.append(
            f"| `{path}` | {'|'.join(sorted(nd.types))} | {nd.count} "
            f"| {len(nd.files) / len(walked):.0%} | {parent_rate(path, nd)} "
            f"| {container} | {'; '.join(nd.examples)} |"
        )
    if len(nodes) > shown:
        lines.append(f"\n… {len(nodes) - shown} more paths — see `schema/paths.json`.")

    lines += ["", "## Candidate field mappings (auto-suggested, uncurated)", ""]
    for target, cands in suggestions.items():
        lines.append(f"### `{target}`")
        lines.append("")
        if not cands:
            lines.append("- NO CANDIDATE FOUND — flag for discrepancy review")
        else:
            lines += [
                f"- `{c['path']}` ({c['types']}, files {c['files']}"
                + (f", e.g. {c['example']}" if c["example"] else "")
                + ")"
                for c in cands
            ]
        lines.append("")

    out_md.write_text("\n".join(lines) + "\n")
    return out_md
