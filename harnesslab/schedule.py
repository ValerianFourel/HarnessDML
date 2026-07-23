"""Seeded random interleaving of the rollout queue (§4.3.1).

Within a job, (config, task, seed) triples are shuffled so no configuration
runs contiguously — breaking time/server-state confounding of component
effects. Deterministic given schedule_seed; tested for the interleaving
property in §8.7.
"""

from __future__ import annotations

import random
from typing import Sequence, TypeVar

T = TypeVar("T")


def interleave(items: Sequence[T], schedule_seed: int) -> list[T]:
    queue = list(items)
    random.Random(schedule_seed).shuffle(queue)
    return queue


def max_run_length(labels: Sequence[str]) -> int:
    """Longest run of identical adjacent labels (diagnostic for the property test)."""
    best = run = 0
    prev = object()
    for lab in labels:
        run = run + 1 if lab == prev else 1
        prev = lab
        best = max(best, run)
    return best
