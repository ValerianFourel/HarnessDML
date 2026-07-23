"""Phase 1–2: schema discovery and ETL to the analysis panel.

Guardrail: NO field names are hardcoded anywhere until the empirical
`schema/SCHEMA.md` exists and has been reviewed. All trace parsing stays in
one module so a doubleml-pyspark port for the full 113 GB corpus is a
transplant, not a rewrite.
"""

from __future__ import annotations


def discover_schema(*args, **kwargs):
    """Phase 1: walk N decrypted traces, emit schema/SCHEMA.md (paths, types,
    presence rates). Written in the next chunk, after the Phase-0 tree review."""
    raise NotImplementedError("Phase 1: written after Phase-0 review (CLAUDE.md).")


def build_panel(*args, **kwargs):
    """Phase 2: one row per rollout -> results/panel/<benchmark>.parquet."""
    raise NotImplementedError("Phase 2: blocked on reviewed schema/SCHEMA.md (CLAUDE.md).")
