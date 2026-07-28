"""Slice-level progress: what fraction of each experiment slice is really done.

`wc -l` on a store answers "how many rollouts exist", which is NOT progress:

* the denominator differs per experiment — 32 configs x tasks x seeds for the
  grid, 4 configs for the thin arm, 6 for the ordering arm — so any single
  hard-coded target is wrong for something (a complete thin-arm store looks
  like "13%" against the grid's denominator);
* a store can hold rollouts on tasks that later left scope (HotpotQA 7405 ->
  3000, ADR 20) — orphans that `aggregate --tasks` drops at harvest, so the
  raw count runs past 100% while in-scope work is still pending;
* it can hold two rollouts for the same (cell, task, seed) written under
  different `rollout_key` schemas — adding `padded_components` to the cell
  identity re-keyed every pre-padding rollout, so those slices re-ran their
  wave-1 tasks once (exactly 16,000 rows for a 32x100x5 slice).

The denominator comes from the experiment spec; in `deep` mode the numerator
comes from reading the store, counting in-scope, unique-cell-task-seed rows.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from . import experiment
from .tasks import load_tasks

ROOT = Path(__file__).resolve().parents[1]

# A rollout's completion identity: the treatment cell plus (task, seed).
# Deliberately NOT rollout_key — the key schema changed once (see module
# docstring) and two rows with different keys can be the same unit of work.
CELL_TASK_SEED = ("config_id", "ordering_id", "template_id", "padded_components",
                  "temp", "task_id", "seed")


def unit_key(rec: dict) -> int:
    """Hash of the (cell, task, seed) unit of work, normalized like aggregate.

    Rows written before the padding arm existed have NO `padded_components`
    key; `aggregate` setdefaults it to '' because that is its exact meaning
    there. Skipping that normalization here made a row and its re-keyed twin
    look like two different units — duplicates read as 0 and unique counts ran
    past the target (qwen/musique: 394,460 "unique" against a 386,720 target).
    """
    return hash(tuple(rec.get(c) if c != "padded_components" else (rec.get(c) or "")
                      for c in CELL_TASK_SEED))


@dataclass
class SliceProgress:
    exp: str
    model: str
    bench: str
    path: Path
    lines: int = 0
    target: int | None = None
    failures: int = 0
    age_s: float | None = None   # since the last write — a live slice is < ~10 min
    # deep-mode only
    in_scope: int | None = None
    unique: int | None = None
    orphans: int | None = None
    dupes: int | None = None
    corrupt: int = 0

    @property
    def done(self) -> int:
        """Best available numerator: unique in-scope work if scanned, else lines."""
        return self.unique if self.unique is not None else self.lines

    @property
    def pct(self) -> float | None:
        if not self.target:
            return None
        return 100.0 * self.done / self.target

    @property
    def remaining(self) -> int | None:
        if self.target is None:
            return None
        return max(0, self.target - self.done)

    # a chain link can sit queued for a while, so idleness is only suspicious
    # after several hours — but an exhausted chain looks exactly like this and
    # cost a day on ministral/gsm8k before anything noticed
    STALL_AFTER_S = 4 * 3600

    @property
    def status(self) -> str:
        if self.target is None:
            return "no-spec"
        if self.done >= self.target:
            return "DONE" if self.unique is not None else "DONE?"
        if self.age_s is not None and self.age_s > self.STALL_AFTER_S:
            return "STALL?"      # unfinished and nothing has written it for hours
        if self.lines >= self.target:  # raw count past target, in-scope unknown
            return "ORPHANS?"
        return "PARTIAL"


def spec_path(exp_dir: str) -> Path | None:
    """Store dirs are named after the spec file: run_experiment.sbatch writes
    to $SCRATCH/harnesslab/$(basename $EXP .yaml)/rollouts_<model>_<bench>."""
    for base in (ROOT / "configs/experiments", ROOT / "configs/experiments/arms"):
        p = base / f"{exp_dir}.yaml"
        if p.exists():
            return p
    return None


def _tasks_file(bench: str) -> Path:
    return ROOT / "configs/tasks" / f"{bench}.jsonl"


def in_scope_ids(spec, bench: str) -> set[str]:
    ids = [t["task_id"] for t in load_tasks(_tasks_file(bench))]
    if spec.n_tasks is not None:
        ids = ids[: spec.n_tasks]
    return set(ids)


def auto_scope(store: Path) -> tuple[set[str] | None, str]:
    """In-scope task ids for a store, derived from its own path.

    `$SCRATCH/harnesslab/<spec-basename>/rollouts_<model>_<bench>` carries
    everything needed to find the spec that produced it — so a harvest can
    apply the right task cap without the operator remembering that HotpotQA
    is capped to 3000 and nothing else is.
    """
    exp = store.parent.name
    bench = store.name[len("rollouts_"):].rpartition("_")[2]
    path = spec_path(exp)
    if path is None or not _tasks_file(bench).exists():
        return None, f"no spec for {exp}/{bench} — harvesting unfiltered"
    spec = experiment.from_yaml(
        path, overrides={"benchmark": bench, "tasks_file": str(_tasks_file(bench))})
    ids = in_scope_ids(spec, bench)
    return ids, (f"{exp}/{bench}: in scope = first {len(ids)} task_ids "
                 f"(n_tasks={spec.n_tasks})")


def slice_target(spec, bench: str) -> int:
    """configs x in-scope tasks x seeds — the spec's own denominator."""
    return len(spec.configs) * len(in_scope_ids(spec, bench)) * spec.k_seeds


def count_lines(path: Path) -> int:
    n = 0
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            n += chunk.count(b"\n")
    return n


def scan_store(path: Path, keep: set[str] | None) -> dict:
    """One pass over rollouts.jsonl: in-scope, unique, orphan, duplicate counts.

    Uniqueness is tracked as a set of `hash(CELL_TASK_SEED tuple)` rather than
    the tuples themselves — 60 MB instead of ~1 GB on a census store, at a
    collision probability of ~n^2/2^65 (negligible at n < 10^7).
    """
    lines = in_scope = orphans = dupes = corrupt = 0
    seen: set[int] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            lines += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                corrupt += 1  # killed mid-write; that rollout simply re-runs
                continue
            if keep is not None and rec.get("task_id") not in keep:
                orphans += 1
                continue
            in_scope += 1
            key = unit_key(rec)
            if key in seen:
                dupes += 1
            else:
                seen.add(key)
    return {"lines": lines, "in_scope": in_scope, "unique": len(seen),
            "orphans": orphans, "dupes": dupes, "corrupt": corrupt}


CACHE_NAME = ".progress_cache.json"
CACHE_FIELDS = ("lines", "in_scope", "unique", "orphans", "dupes", "corrupt")


def _load_cache(root: Path) -> dict:
    p = Path(root) / CACHE_NAME
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}          # a corrupt cache costs a rescan, never a wrong number


def _save_cache(root: Path, cache: dict) -> None:
    p = Path(root) / CACHE_NAME
    try:
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache))
        tmp.replace(p)     # atomic: a killed run never leaves a half-written cache
    except OSError:
        pass               # read-only root is fine; caching is an optimization


def _cache_key(jsonl: Path, keep: set[str] | None) -> dict:
    """Stores are append-only, so (size, mtime) identifies their content, and
    the scope size invalidates a cached scan taken under a different task cap."""
    st = jsonl.stat()
    return {"size": st.st_size, "mtime_ns": st.st_mtime_ns,
            "scope_n": -1 if keep is None else len(keep)}


def walk(root: Path, deep: bool = False, only: str | None = None,
         use_cache: bool = True, workers: int | None = None) -> list[SliceProgress]:
    """Every rollout store under <root>/<exp>/rollouts_<model>_<bench>/.

    A deep walk reads every byte of every store — minutes on this dataset, and
    most of it wasted: a finished slice has not changed in days. Unchanged
    stores are served from a cache keyed on (size, mtime, scope), and the ones
    that did change are scanned in parallel.
    """
    out: list[SliceProgress] = []
    cache = _load_cache(root) if (deep and use_cache) else {}
    pending: list[tuple[SliceProgress, Path, set[str] | None, str]] = []
    for store in sorted(Path(root).glob("*/rollouts_*")):
        jsonl = store / "rollouts.jsonl"
        if not jsonl.exists():
            continue
        rel = f"{store.parent.name}/{store.name}"
        if only and only not in rel:
            continue
        exp = store.parent.name
        model, _, bench = store.name[len("rollouts_"):].rpartition("_")
        sp = SliceProgress(exp=exp, model=model, bench=bench, path=store)
        fail = store / "failures.jsonl"
        sp.failures = count_lines(fail) if fail.exists() else 0
        sp.age_s = max(0.0, time.time() - jsonl.stat().st_mtime)

        spec = None
        path = spec_path(exp)
        if path is not None and _tasks_file(bench).exists():
            try:
                # model_id is deliberately NOT overridden: the target depends
                # only on configs x tasks x seeds, and resolve_model() would
                # reject a store written by a model since dropped from the
                # registry — losing the target for data we still have.
                spec = experiment.from_yaml(
                    path, overrides={"benchmark": bench,
                                     "tasks_file": str(_tasks_file(bench))})
                sp.target = slice_target(spec, bench)
            except Exception:  # unknown bench for this spec, bad override, ...
                spec = None

        if deep:
            keep = in_scope_ids(spec, bench) if spec is not None else None
            key = _cache_key(jsonl, keep)
            hit = cache.get(rel)
            if hit and all(hit.get(k) == v for k, v in key.items()):
                _apply_stats(sp, hit)
            else:
                pending.append((sp, jsonl, keep, rel))
        else:
            sp.lines = count_lines(jsonl)
        out.append(sp)

    if pending:
        for sp, jsonl, keep, rel in _scan_all(pending, workers):
            cache[rel] = {**_cache_key(jsonl, keep),
                          **{k: getattr(sp, k) for k in CACHE_FIELDS}}
        if use_cache:
            _save_cache(root, cache)
    return out


def _apply_stats(sp: SliceProgress, stats: dict) -> None:
    sp.lines = stats["lines"]
    sp.in_scope = stats["in_scope"]
    sp.unique = stats["unique"]
    sp.orphans = stats["orphans"]
    sp.dupes = stats["dupes"]
    sp.corrupt = stats["corrupt"]


def _scan_all(pending: list, workers: int | None):
    """Scan the changed stores, in parallel when there is more than one.

    json parsing is CPU-bound and the GIL makes threads useless here, so this
    is processes; a failure of the pool falls back to a serial scan rather
    than reporting nothing.
    """
    if workers is None:
        workers = min(8, (os.cpu_count() or 2))
    if len(pending) > 1 and workers > 1:
        try:
            from concurrent.futures import ProcessPoolExecutor

            with ProcessPoolExecutor(max_workers=min(workers, len(pending))) as pool:
                futures = {pool.submit(scan_store, jsonl, keep): (sp, jsonl, keep, rel)
                           for sp, jsonl, keep, rel in pending}
                for fut, item in futures.items():
                    _apply_stats(item[0], fut.result())
                    yield item
            return
        except Exception:
            pass          # oversubscribed node, no fork, ... — do it serially
    for sp, jsonl, keep, rel in pending:
        _apply_stats(sp, scan_store(jsonl, keep))
        yield sp, jsonl, keep, rel


def load_gates(path: Path | None = None) -> dict:
    """configs/gates.yaml — the committed difficulty-gate rulings (§4.4)."""
    import yaml

    p = path or ROOT / "configs/gates.yaml"
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def gaps(rows: list[SliceProgress], gates: dict) -> list[dict]:
    """Slices the gate says belong in the census but that no store covers yet,
    plus census slices still short of their target. The 'what is left' list."""
    have = {(r.exp, r.model, r.bench): r for r in rows}
    # a 'thin' ruling is satisfied by the thin arm's store, not the grid's
    exp_for = {"census": "mvp_grid", "thin": "mvp_thin_gsm8k"}
    out = []
    for model, benches in (gates.get("models") or {}).items():
        for bench, ruling in (benches or {}).items():
            status = (ruling or {}).get("status")
            if status not in exp_for:
                continue
            r = have.get((exp_for[status], model, bench))
            spec_file = ("configs/experiments/mvp_grid.yaml" if status == "census"
                         else "configs/experiments/mvp_thin_gsm8k.yaml")
            submit = (f"EXP={spec_file} MODEL_ID={model} BENCH={bench} "
                      "sbatch slurm/run_experiment.sbatch")
            if r is None:
                out.append({"model": model, "bench": bench, "state": "NO STORE",
                            "have": 0, "target": None, "submit": submit,
                            "note": (ruling or {}).get("note", "")})
            elif r.status != "DONE" and r.remaining:
                note = f"{r.remaining} rollouts left"
                if r.status == "STALL?":
                    note += f" — nothing has written it for {r.age_s / 3600:.0f} h; " \
                            "chain exhausted?"
                out.append({"model": model, "bench": bench, "state": r.status,
                            "have": r.done, "target": r.target, "submit": submit,
                            "note": note})
    # stalled slices first: they need a resubmission, the others need patience
    return sorted(out, key=lambda g: (g["state"] != "STALL?", g["model"], g["bench"]))


CENSUS_EXPS = ("mvp_grid", "mvp_thin_gsm8k")


def _age(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    for unit, size in (("m", 60), ("h", 3600), ("d", 86400)):
        if seconds < size * 60 or unit == "d":
            return f"{seconds / size:.0f}{unit}"
    return "-"


BANDS = ("hotpotqa", "musique", "gsm8k", "math")
STATUS_ABBR = {"census": "CEN", "thin": "THIN", "dropped": "DROP", "bridge_only": "BRDG",
               "pending_gate": "GATE?", "unprobed": "PRB?", "blocked": "BLK",
               "out_of_scope": "OOS"}
TIER_ORDER = {"F": 0, "G": 1, "B": 2, "S": 3}


_TARGET_MEMO: dict[tuple[str, str], int] = {}


def ruling_target(status: str, bench: str) -> int:
    """Rollouts a gate ruling implies, whether or not a store exists yet — so
    a gated model that has never run shows its outstanding work, not a dash."""
    exp = {"census": "mvp_grid", "thin": "mvp_thin_gsm8k"}.get(status)
    if exp is None or not _tasks_file(bench).exists():
        return 0
    if (exp, bench) not in _TARGET_MEMO:
        spec = experiment.from_yaml(
            spec_path(exp), overrides={"benchmark": bench,
                                       "tasks_file": str(_tasks_file(bench))})
        _TARGET_MEMO[(exp, bench)] = slice_target(spec, bench)
    return _TARGET_MEMO[(exp, bench)]


def roster(rows: list[SliceProgress], gates: dict, registry: dict, deep: bool = False) -> str:
    """One line per registry model: gate ruling and census progress per band.

    The slice table answers "which stores exist"; this answers "where does
    every model in the roster stand" — including the ones with no store at
    all, which are exactly the ones at risk of being forgotten (a model that
    was probed but never piloted leaves no trace in a store-driven view).
    """
    census = {(r.model, r.bench): r for r in rows if r.exp in CENSUS_EXPS}
    piloted = {r.model for r in rows if r.exp == "pilot"}
    rulings = gates.get("models") or {}

    head = (f"{'model':23} {'tier':4} {'pilot':5} "
            + " ".join(f"{b:^12.12}" for b in BANDS)
            + f" {'census done / target':>26}")
    out = [head, "-" * len(head)]
    grand_done = grand_target = 0
    for model in sorted(registry, key=lambda m: (TIER_ORDER.get(registry[m].get("tier"), 9), m)):
        cells, done, target = [], 0, 0
        for band in BANDS:
            status = (rulings.get(model, {}).get(band) or {}).get("status")
            r = census.get((model, band))
            band_target = (r.target if r is not None and r.target
                           else ruling_target(status, band))
            target += band_target
            band_done = min(r.done, band_target) if (r is not None and band_target) else 0
            done += band_done
            abbr = STATUS_ABBR.get(status, "-" if status is None else status)
            pct = (f"{100.0 * band_done / band_target:5.1f}%" if band_target else "      ")
            cells.append(f"{abbr:5}{pct:>7}")
        totals = (f"{done:>11,} /{target:>11,}" if target else
                  f"{'not in the census':>26}")
        grand_done += done
        grand_target += target
        out.append(f"{model:23.23} {registry[model].get('tier', '?'):4} "
                   f"{'yes' if model in piloted else '-':5} " + " ".join(cells) + f" {totals}")
    pct = f"{100.0 * grand_done / grand_target:.1f}%" if grand_target else "-"
    out += ["-" * len(head),
            f"{'ALL GATED MODELS':23} {'':4} {'':5} " + " " * (13 * len(BANDS) - 1)
            + f" {grand_done:>11,} /{grand_target:>11,}  {pct}",
            "",
            "CEN census · THIN 4-config thin arm · DROP gate failed · BRDG bridge arm only",
            "GATE? pilot ran, ruling unread · PRB? not probed · BLK cannot serve · - no ruling",
            f"progress numerator: {'unique in-scope work' if deep else 'raw lines (upper bound)'}"]
    return "\n".join(out)


def format_table(rows: list[SliceProgress], deep: bool) -> str:
    head = (f"{'exp':16} {'model':22} {'bench':9} {'have':>10} {'target':>10} "
            f"{'%':>6} {'status':9} {'age':>5}")
    if deep:
        head += f" {'orphan':>8} {'dupe':>7}"
    head += "  fail"
    lines = [head, "-" * len(head)]
    for r in sorted(rows, key=lambda r: (r.exp, -(r.pct or -1), -r.lines)):
        pct = f"{r.pct:5.1f}%" if r.pct is not None else "     -"
        tgt = f"{r.target:10d}" if r.target is not None else "         -"
        line = (f"{r.exp:16.16} {r.model:22.22} {r.bench:9.9} {r.done:10d} {tgt} "
                f"{pct} {r.status:9} {_age(r.age_s):>5}")
        if deep:
            line += f" {r.orphans or 0:8d} {r.dupes or 0:7d}"
        line += f"  {r.failures}" if r.failures else ""
        lines.append(line)
    return "\n".join(lines)


def summarize(rows: list[SliceProgress], deep: bool = False, gates: dict | None = None) -> str:
    """How much of the census is done, per model and overall.

    In shallow mode the numerator is raw lines, which overstates any slice
    holding orphans or re-key duplicates — HotpotQA is the only band that can
    hold orphans (its 7405-task pool is the only one above the 3000 cap), but
    every pre-padding slice holds duplicates. --deep replaces it with unique
    in-scope work.
    """
    census = [r for r in rows if r.exp in CENSUS_EXPS]
    by_model: dict[str, list[int]] = {}
    for r in census:
        acc = by_model.setdefault(r.model, [0, 0])
        acc[0] += min(r.done, r.target) if r.target else r.done
        acc[1] += r.target or 0
    # Denominator from the RULINGS when we have them, not from the stores that
    # happen to exist: a gated band whose chain has not produced a first
    # rollout yet has no store, and counting only stores quietly shrinks the
    # target — the same run printed 45.4% here against the roster's 39.7%.
    for model, benches in ((gates or {}).get("models") or {}).items():
        ruled = sum(ruling_target((r or {}).get("status"), b) for b, r in (benches or {}).items())
        if ruled:
            by_model.setdefault(model, [0, 0])[1] = ruled
    done = sum(a[0] for a in by_model.values())
    target = sum(a[1] for a in by_model.values())
    live = sum(1 for r in rows if r.age_s is not None and r.age_s < 600)
    unit = "unique in-scope rollouts" if deep else "raw lines (upper bound)"
    out = [f"CENSUS PROGRESS — {unit}",
           f"{'model':24} {'done':>12} {'target':>12}     %"]
    for model, (d, t) in sorted(by_model.items(), key=lambda kv: -kv[1][0]):
        pct = f"{100.0 * d / t:5.1f}%" if t else "    -"
        out.append(f"{model:24} {d:>12,} {t:>12,} {pct}")
    pct = f"{100.0 * done / target:5.1f}%" if target else "    -"
    out += [f"{'TOTAL':24} {done:>12,} {target:>12,} {pct}",
            "",
            f"slices: {len(rows)} total, {live} written in the last 10 min"]
    if not deep:
        out.append("(--deep for the real numerator: orphans and duplicates removed)")
    return "\n".join(out)
