"""Phase 1–2: schema discovery and ETL to the analysis panel.

Guardrail: NO field names are hardcoded anywhere until the empirical
`schema/SCHEMA.md` exists and has been reviewed; Phase-2 ETL reads only the
curated `schema/field_mapping.yaml`. All trace parsing stays in one module so
a doubleml-pyspark port for the full 113 GB corpus is a transplant, not a
rewrite.
"""

from __future__ import annotations

from .discover_schema import discover_schema  # noqa: F401


def build_panel(*args, **kwargs):
    """Phase 2: one row per rollout -> results/panel/<benchmark>.parquet."""
    raise NotImplementedError(
        "Phase 2: blocked on reviewed schema/SCHEMA.md and curated "
        "schema/field_mapping.yaml (CLAUDE.md)."
    )
