"""Phase 4: config-driven DML estimation (one estimand per config yaml).

Every entry point here MUST, in order:
  1. guards.require_design_notes()            — Phase-3 gate
  2. guards.validate_covariates(X, D)         — post-treatment hard error
before constructing any DoubleML object. Cluster-robust at task_id, always.
"""

from __future__ import annotations


def estimate(*args, **kwargs):
    raise NotImplementedError("Phase 4: blocked on Phase-3 design notes (CLAUDE.md).")
