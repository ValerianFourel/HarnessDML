"""Panel access with the causal-role guard (§5, §8.9).

`load_panel(covariates=...)` hard-errors unless every requested covariate has
role treatment, context, or pre_treatment in schema/column_roles.yaml.
Outcome, post_treatment (mediators/cost), and meta columns are NEVER
covariates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import polars as pl
import yaml

_SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"
ALLOWED_COVARIATE_ROLES = {"treatment", "context", "pre_treatment"}


class RoleError(ValueError):
    """A column was requested in a role its registry entry forbids."""


def load_column_roles(path: Path | str | None = None) -> dict[str, str]:
    p = Path(path) if path else _SCHEMA_DIR / "column_roles.yaml"
    raw = yaml.safe_load(p.read_text())
    return {col: spec["role"] for col, spec in raw.items()}


def panel_columns(path: Path | str | None = None) -> list[str]:
    p = Path(path) if path else _SCHEMA_DIR / "panel_schema.yaml"
    return list(yaml.safe_load(p.read_text())["panel"])


def validate_covariates(
    covariates: Iterable[str], roles: Mapping[str, str] | None = None
) -> None:
    roles = dict(roles) if roles is not None else load_column_roles()
    problems = []
    for col in covariates:
        if col not in roles:
            problems.append(f"{col}: not in schema/column_roles.yaml")
        elif roles[col] not in ALLOWED_COVARIATE_ROLES:
            problems.append(
                f"{col}: role {roles[col]!r} may never be a covariate "
                "(mediator/outcome/meta)"
            )
    if problems:
        raise RoleError("covariate validation failed:\n  - " + "\n  - ".join(problems))


def validate_record(record: Mapping, schema_path: Path | str | None = None) -> list[str]:
    """Missing/extra keys vs the panel schema (used by aggregate)."""
    expected = set(panel_columns(schema_path))
    got = set(record)
    problems = [f"missing column {c!r}" for c in sorted(expected - got)]
    problems += [f"unexpected column {c!r}" for c in sorted(got - expected)]
    return problems


def load_panel(
    path: Path | str,
    covariates: Iterable[str] | None = None,
    roles_path: Path | str | None = None,
) -> pl.DataFrame:
    if covariates is not None:
        validate_covariates(covariates, load_column_roles(roles_path))
    return pl.read_parquet(path)
