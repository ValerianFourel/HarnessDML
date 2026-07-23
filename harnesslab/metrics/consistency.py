"""Distributional consistency metrics over K repeated seeds (§5).

All functions are pure and fixture-tested against hand-computed values (§8.5).
Cell-level assembly (grouping rows into these inputs) lives in aggregate.
"""

from __future__ import annotations

import math
from collections import Counter
from itertools import combinations
from typing import Mapping, Sequence


# ── outcome consistency ─────────────────────────────────────────────────────
def c_out(correct_by_task: Mapping[str, Sequence[bool]]) -> float:
    """mean_t (2·p̂_t − 1)² — 1 when deterministic either way, 0 at p̂=1/2."""
    vals = []
    for outcomes in correct_by_task.values():
        p = sum(outcomes) / len(outcomes)
        vals.append((2 * p - 1) ** 2)
    return sum(vals) / len(vals)


def pass_at_k(correct_by_task: Mapping[str, Sequence[bool]]) -> float:
    return sum(any(v) for v in correct_by_task.values()) / len(correct_by_task)


def pass_all_k(correct_by_task: Mapping[str, Sequence[bool]]) -> float:
    return sum(all(v) for v in correct_by_task.values()) / len(correct_by_task)


# ── trajectory consistency ──────────────────────────────────────────────────
def action_type_dist(seq: Sequence[str]) -> dict[str, float]:
    if not seq:
        return {}
    counts = Counter(seq)
    n = len(seq)
    return {k: v / n for k, v in counts.items()}


def jsd(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    """Jensen–Shannon divergence, base 2, in [0, 1]. Empty-vs-empty = 0;
    empty-vs-nonempty = 1 (maximally different)."""
    if not p and not q:
        return 0.0
    if not p or not q:
        return 1.0
    keys = set(p) | set(q)

    def kl(a: Mapping[str, float], b: dict[str, float]) -> float:
        return sum(a[k] * math.log2(a[k] / b[k]) for k in a if a.get(k, 0) > 0)

    m = {k: (p.get(k, 0) + q.get(k, 0)) / 2 for k in keys}
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def levenshtein(a: Sequence[str], b: Sequence[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def normalized_levenshtein(a: Sequence[str], b: Sequence[str]) -> float:
    if not a and not b:
        return 0.0
    return levenshtein(a, b) / max(len(a), len(b))


def _mean_pairwise(values: Sequence, dist) -> float:
    pairs = list(combinations(range(len(values)), 2))
    if not pairs:
        return 0.0
    return sum(dist(values[i], values[j]) for i, j in pairs) / len(pairs)


def c_traj_d(seqs_by_task: Mapping[str, Sequence[Sequence[str]]]) -> float:
    """1 − mean (over tasks) of mean pairwise JSD between the seeds'
    action-type distributions."""
    per_task = [
        _mean_pairwise([action_type_dist(s) for s in seqs], jsd)
        for seqs in seqs_by_task.values()
    ]
    return 1.0 - sum(per_task) / len(per_task)


def c_traj_s(seqs_by_task: Mapping[str, Sequence[Sequence[str]]]) -> float:
    """1 − mean (over tasks) of mean pairwise normalized Levenshtein between
    the seeds' action sequences."""
    per_task = [
        _mean_pairwise(list(seqs), normalized_levenshtein)
        for seqs in seqs_by_task.values()
    ]
    return 1.0 - sum(per_task) / len(per_task)


# ── resource consistency ────────────────────────────────────────────────────
def cv(values: Sequence[float]) -> float:
    """Coefficient of variation (population sd / |mean|); all-zero → 0."""
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    sd = math.sqrt(var)
    if mean == 0:
        return 0.0 if sd == 0 else math.inf
    return sd / abs(mean)


def c_res(resources_by_task: Mapping[str, Mapping[str, Sequence[float]]]) -> float:
    """exp(−mean CV) over resources × tasks (§5). Input:
    {resource: {task: [values across seeds]}}; tasks need ≥ 2 values."""
    cvs: list[float] = []
    for per_task in resources_by_task.values():
        for values in per_task.values():
            if len(values) >= 2:
                cvs.append(cv(values))
    if not cvs:
        return float("nan")
    return math.exp(-sum(cvs) / len(cvs))
