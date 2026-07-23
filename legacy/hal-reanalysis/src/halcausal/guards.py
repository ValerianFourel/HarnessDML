"""Causal-discipline guards (CLAUDE.md guardrails 1 and Phase-3 gate).

`schema/column_roles.yaml` is the single source of truth for what a column
*is*. Estimation code must run `validate_covariates()` before any DoubleML
object is constructed, and `require_design_notes()` before any estimation run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import yaml

from .paths import repo_root, results_dir

VALID_ROLES = {"treatment", "outcome", "pre_treatment", "post_treatment", "id"}

# Roles that may never enter the covariate set X:
#  - post_treatment: mediators/realized quantities (steps, tool calls, tokens
#    consumed, termination reason) — conditioning on them biases the estimand.
#  - outcome: outcomes are modeled, never conditioned on.
#  - id: identifiers cluster or index; task fixed effects enter via within-task
#    transforms, never as a raw column.
FORBIDDEN_IN_X = {"post_treatment", "outcome", "id"}


class ColumnRoleError(ValueError):
    """Registry problem: unknown column, invalid role, non-treatment used as D."""


class CovariateValidationError(ColumnRoleError):
    """X contains a column whose role forbids it (post-treatment, outcome, id)."""


class DesignNotesMissingError(FileNotFoundError):
    """Phase-4 estimation attempted before Phase-3 design notes exist."""


def load_column_roles(path: Path | str | None = None) -> dict[str, str]:
    """Load {column: role} from the registry; reject unknown roles loudly."""
    path = Path(path) if path is not None else repo_root() / "schema" / "column_roles.yaml"
    raw = yaml.safe_load(path.read_text())
    roles: dict[str, str] = {}
    for col, spec in raw.items():
        role = spec["role"] if isinstance(spec, Mapping) else spec
        if role not in VALID_ROLES:
            raise ColumnRoleError(
                f"{col}: role {role!r} not in {sorted(VALID_ROLES)} ({path})"
            )
        roles[col] = role
    return roles


def validate_covariates(
    x_cols: Iterable[str],
    treatment: str,
    roles: Mapping[str, str] | None = None,
) -> None:
    """Hard-error unless every column in X is admissible for treatment D.

    Admissible: role `pre_treatment`, or role `treatment` for a column other
    than the active treatment (co-assigned config knobs may be conditioned on;
    whether they *should* be is an estimand-level decision made in the config).
    """
    roles = dict(roles) if roles is not None else load_column_roles()

    if treatment not in roles:
        raise ColumnRoleError(f"treatment {treatment!r} is not in the column registry")
    if roles[treatment] != "treatment":
        raise ColumnRoleError(
            f"{treatment!r} has role {roles[treatment]!r}; only role 'treatment' may be D"
        )

    problems = []
    for col in x_cols:
        if col == treatment:
            problems.append(f"{col}: the active treatment cannot appear in X")
        elif col not in roles:
            problems.append(
                f"{col}: unregistered — add it to schema/column_roles.yaml before use"
            )
        elif roles[col] in FORBIDDEN_IN_X:
            problems.append(f"{col}: role {roles[col]!r} may never enter X")
    if problems:
        raise CovariateValidationError(
            "covariate validation failed:\n  - " + "\n  - ".join(problems)
        )


def require_design_notes(path: Path | str | None = None) -> Path:
    """Phase-3 gate: estimation refuses to run without reviewed design notes."""
    p = Path(path) if path is not None else results_dir() / "diagnostics" / "design_notes.md"
    if not p.is_file():
        raise DesignNotesMissingError(
            f"{p} does not exist. Phase-3 design diagnostics (assignment mechanism, "
            "estimable strata) must be written and reviewed before estimation "
            "(CLAUDE.md, Phase 3)."
        )
    return p
