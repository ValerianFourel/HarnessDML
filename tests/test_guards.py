"""Guardrail 1: the post-treatment/outcome/id covariate guard, and the
Phase-3 design-notes gate. These tests also lock the shipped registry."""

import pytest

from halcausal import guards


@pytest.fixture(scope="module")
def roles():
    return guards.load_column_roles()  # the real schema/column_roles.yaml


def test_registry_covers_planned_panel_columns(roles):
    expected = {
        "rollout_id": "id",
        "task_id": "id",
        "benchmark": "pre_treatment",
        "domain": "pre_treatment",
        "model": "treatment",
        "model_family": "pre_treatment",
        "reasoning_effort": "treatment",
        "scaffold": "treatment",
        "temperature": "treatment",
        "success": "outcome",
        "total_cost_usd": "outcome",
        "wall_clock_s": "outcome",
        "completion_tokens": "outcome",
        "prompt_tokens": "post_treatment",
        "reasoning_tokens": "post_treatment",
        "n_llm_calls": "post_treatment",
        "n_tool_calls": "post_treatment",
        "termination_reason": "post_treatment",
        "task_prompt_len": "pre_treatment",
        "task_difficulty": "pre_treatment",
    }
    for col, role in expected.items():
        assert roles.get(col) == role, f"{col}: expected {role}, got {roles.get(col)}"


def test_valid_covariate_set_passes(roles):
    guards.validate_covariates(
        ["benchmark", "domain", "model", "task_prompt_len", "task_difficulty"],
        treatment="reasoning_effort",
        roles=roles,
    )


def test_post_treatment_in_x_hard_errors(roles):
    with pytest.raises(guards.CovariateValidationError, match="n_tool_calls"):
        guards.validate_covariates(
            ["benchmark", "n_tool_calls"], treatment="reasoning_effort", roles=roles
        )


def test_outcome_in_x_hard_errors(roles):
    with pytest.raises(guards.CovariateValidationError, match="success"):
        guards.validate_covariates(["success"], treatment="scaffold", roles=roles)


def test_id_in_x_hard_errors(roles):
    with pytest.raises(guards.CovariateValidationError, match="task_id"):
        guards.validate_covariates(["task_id"], treatment="scaffold", roles=roles)


def test_active_treatment_in_x_hard_errors(roles):
    with pytest.raises(guards.CovariateValidationError, match="active treatment"):
        guards.validate_covariates(
            ["reasoning_effort"], treatment="reasoning_effort", roles=roles
        )


def test_unregistered_column_hard_errors(roles):
    with pytest.raises(guards.CovariateValidationError, match="unregistered"):
        guards.validate_covariates(["mystery_col"], treatment="scaffold", roles=roles)


def test_co_treatment_as_covariate_is_allowed(roles):
    # model is a covariate whenever it is not the active treatment
    guards.validate_covariates(["model"], treatment="reasoning_effort", roles=roles)


def test_non_treatment_cannot_be_d(roles):
    with pytest.raises(guards.ColumnRoleError, match="only role 'treatment'"):
        guards.validate_covariates(["benchmark"], treatment="success", roles=roles)


def test_invalid_role_in_registry_rejected(tmp_path):
    bad = tmp_path / "column_roles.yaml"
    bad.write_text("foo: {role: mediator}\n")
    with pytest.raises(guards.ColumnRoleError, match="mediator"):
        guards.load_column_roles(bad)


def test_design_notes_gate(tmp_path):
    missing = tmp_path / "design_notes.md"
    with pytest.raises(guards.DesignNotesMissingError, match="Phase-3"):
        guards.require_design_notes(missing)
    missing.write_text("assignment mechanism: ...")
    assert guards.require_design_notes(missing) == missing
