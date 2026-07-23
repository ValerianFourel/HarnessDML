"""§8.9 — load_panel hard-errors on post_treatment/outcome/meta as covariate."""

import pytest

from harnesslab.panel import RoleError, load_panel, panel_columns, validate_covariates


def test_allowed_covariates_pass():
    validate_covariates(["comp_P", "comp_T", "benchmark", "band", "task_id",
                         "model_family", "task_difficulty_calib"])


@pytest.mark.parametrize("col", ["tokens_out", "n_turns", "action_seq", "wall_s"])
def test_post_treatment_as_covariate_hard_errors(col):
    with pytest.raises(RoleError, match=col):
        validate_covariates([col])


@pytest.mark.parametrize("col", ["y", "em", "confidence"])
def test_outcome_as_covariate_hard_errors(col):
    with pytest.raises(RoleError, match=col):
        validate_covariates([col])


def test_meta_and_unknown_rejected():
    with pytest.raises(RoleError, match="rollout_key"):
        validate_covariates(["rollout_key"])
    with pytest.raises(RoleError, match="not in schema"):
        validate_covariates(["definitely_not_a_column"])


def test_load_panel_validates_before_touching_the_file():
    with pytest.raises(RoleError):  # NOT FileNotFoundError — guard runs first
        load_panel("does_not_exist.parquet", covariates=["tokens_out"])


def test_panel_columns_ordered_and_complete():
    cols = panel_columns()
    assert len(cols) == 48
    assert cols[0] == "rollout_key"
