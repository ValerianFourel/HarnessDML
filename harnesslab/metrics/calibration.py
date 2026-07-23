"""Calibration metrics over elicited confidence (§5). Pure, fixture-tested.

Inputs use confidence on [0, 1] and boolean correctness; rows with
confidence_source='fallback' are excluded upstream (documented in REPORTs).
"""

from __future__ import annotations

from typing import Sequence


def ece(confidence: Sequence[float], correct: Sequence[bool], n_bins: int = 10) -> float:
    """Expected calibration error, equal-width bins, last bin inclusive."""
    assert len(confidence) == len(correct) and confidence
    bins: list[list[int]] = [[] for _ in range(n_bins)]
    for i, c in enumerate(confidence):
        b = min(int(c * n_bins), n_bins - 1)
        bins[b].append(i)
    n = len(confidence)
    total = 0.0
    for members in bins:
        if not members:
            continue
        acc = sum(correct[i] for i in members) / len(members)
        conf = sum(confidence[i] for i in members) / len(members)
        total += (len(members) / n) * abs(acc - conf)
    return total


def auroc(confidence: Sequence[float], correct: Sequence[bool]) -> float | None:
    """Rank-based AUROC with average ranks for ties; None if degenerate."""
    n_pos = sum(correct)
    n_neg = len(correct) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    order = sorted(range(len(confidence)), key=lambda i: confidence[i])
    ranks = [0.0] * len(confidence)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and confidence[order[j + 1]] == confidence[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1  # 1-based average rank across the tie group
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    rank_sum_pos = sum(r for r, c in zip(ranks, correct) if c)
    return (rank_sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def brier(confidence: Sequence[float], correct: Sequence[bool]) -> float:
    assert len(confidence) == len(correct) and confidence
    return sum((c - float(y)) ** 2 for c, y in zip(confidence, correct)) / len(confidence)
