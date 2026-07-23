"""Phase 0: panel schema and role registry are complete, valid, and 1:1."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLES = yaml.safe_load((ROOT / "schema" / "column_roles.yaml").read_text())
SCHEMA = yaml.safe_load((ROOT / "schema" / "panel_schema.yaml").read_text())

VALID_ROLES = {"treatment", "context", "pre_treatment", "outcome", "post_treatment", "meta"}
VALID_DTYPES = {"str", "int64", "float64", "bool"}


def test_every_role_is_valid():
    for col, spec in ROLES.items():
        assert spec["role"] in VALID_ROLES, f"{col}: bad role {spec['role']!r}"


def test_registry_and_panel_schema_cover_each_other_exactly():
    panel_cols = set(SCHEMA["panel"])
    role_cols = set(ROLES)
    assert panel_cols == role_cols, (
        f"only in panel_schema: {sorted(panel_cols - role_cols)}; "
        f"only in column_roles: {sorted(role_cols - panel_cols)}"
    )


def test_panel_dtypes_valid():
    for col, spec in SCHEMA["panel"].items():
        assert spec["dtype"] in VALID_DTYPES, f"{col}: bad dtype {spec['dtype']!r}"
        assert isinstance(spec["nullable"], bool), f"{col}: nullable must be bool"


def test_treatments_are_exactly_the_design():
    treatments = {c for c, s in ROLES.items() if s["role"] == "treatment"}
    assert treatments == {
        "comp_P", "comp_T", "comp_M", "comp_SR", "comp_R",
        "config_id", "ordering_id", "template_id",
    }


def test_mediators_and_cost_measures_are_post_treatment():
    for col in ("n_turns", "tokens_in", "tokens_out", "n_tool_calls",
                "n_parse_failures", "action_seq", "wall_s", "gpu_seconds"):
        assert ROLES[col]["role"] == "post_treatment", col


def test_y_decomposition_outcomes_present():
    for col in ("y", "em", "answered", "finish_reason", "confidence"):
        assert ROLES[col]["role"] == "outcome", col


def test_cell_metrics_section_has_reliability_functionals():
    cols = SCHEMA["cell_metrics"]["columns"]
    for m in ("c_out", "c_traj_d", "c_traj_s", "c_res_uncond", "c_res_cond",
              "pass_at_k", "pass_all_k", "ece_10bin", "auroc", "brier"):
        assert m in cols, m


def test_model_registry_well_formed():
    models = yaml.safe_load((ROOT / "configs" / "models.yaml").read_text())["models"]
    required = {"hf_id", "revision", "verify", "family", "tier", "serving_mode",
                "params_b_total", "params_b_active", "license_note", "note"}
    for key, m in models.items():
        missing = required - set(m)
        assert not missing, f"{key}: missing {sorted(missing)}"
        assert m["tier"] in {"F", "G", "B", "S"}, key
        assert m["serving_mode"] in {"one_gpu", "one_node_tp4", "multi_node"}, key
        assert isinstance(m["verify"], bool), key
        if m["tier"] == "S":
            assert m.get("enabled") is False, f"{key}: Tier S must be enabled: false (out of MVP scope)"
    assert models["llama_3_1_8b"]["tier"] == "B"  # CCI's validated cell, bridge only
