"""Phase-3 provisioning units: fits-check, multi-endpoint client, spec
overrides + task slicing, seeded task sampling."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

from harnesslab.client import MockClient, MultiEndpointClient
from harnesslab.experiment import from_yaml, load_registry
from harnesslab.fits import check_registry, required_gb, serving_mode_for

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "hpc"))
from build_tasks import sample_indices  # noqa: E402


def test_serving_mode_thresholds():
    assert serving_mode_for(8) == "one_gpu"       # 21.6 GB
    assert serving_mode_for(27) == "one_gpu"      # 72.9 GB < 86.4
    assert serving_mode_for(109) == "one_node_tp4"
    assert serving_mode_for(117) == "one_node_tp4"
    assert serving_mode_for(400) == "multi_node"
    assert required_gb(100) == pytest.approx(270.0)


def test_registry_declared_modes_pass_fits_check():
    rows = check_registry(load_registry())
    mismatches = [r for r in rows if not r["ok"]]
    assert mismatches == [], mismatches


def test_multi_endpoint_round_robin():
    a = MockClient(lambda m, s: "from-a")
    b = MockClient(lambda m, s: "from-b")
    client = MultiEndpointClient([a, b])

    async def go():
        outs = []
        for _ in range(4):
            res = await client.chat(
                [{"role": "user", "content": "x"}],
                temperature=0.1, top_p=0.9, max_tokens=8, seed=0,
            )
            outs.append(res.text)
        return outs

    assert asyncio.run(go()) == ["from-a", "from-b", "from-a", "from-b"]
    assert len(a.calls) == 2 and len(b.calls) == 2


def test_spec_overrides_and_n_tasks():
    spec = from_yaml(
        "tests/fixtures/exp_mock_qa.yaml",
        overrides={"exp_id": "ovr", "n_tasks": 2, "k_seeds": 1},
    )
    assert spec.exp_id == "ovr" and spec.n_tasks == 2 and spec.k_seeds == 1


def test_pilot_and_smoke_specs_parse():
    pilot = from_yaml("configs/experiments/pilot.yaml")
    assert len(pilot.configs) == 4 and pilot.n_tasks == 20 and pilot.k_seeds == 2
    assert {c.config_id for c in pilot.configs} == {"BARE", "T", "T+SR+R", "P+T+M+SR+R"}
    smoke = from_yaml("configs/experiments/smoke_live.yaml")
    assert smoke.n_tasks == 5 and len(smoke.configs) == 2


def test_mvp_grid_specs_parse():
    grid = from_yaml("configs/experiments/mvp_grid.yaml")
    ids = [c.config_id for c in grid.configs]
    assert len(ids) == 32 and len(set(ids)) == 32          # full factorial, no dupes
    assert grid.k_seeds == 5 and grid.n_tasks is None
    assert grid.throughput_rollouts_per_node_hour == 4000  # budget unlocked
    thin = from_yaml("configs/experiments/mvp_thin_gsm8k.yaml")
    assert len(thin.configs) == 4 and thin.benchmark == "gsm8k"
    topup = from_yaml("configs/experiments/mvp_headline_topup.yaml")
    assert topup.k_seeds == 10 and topup.exp_id == "mvp_grid"  # same store as grid
    assert {c.config_id for c in topup.configs} == {c.config_id for c in thin.configs}


def test_served_model_name_resolves_hf_id():
    from harnesslab.experiment import served_model_name

    pilot = from_yaml("configs/experiments/pilot.yaml")
    # never the registry key
    assert served_model_name(pilot) == "mistralai/Mistral-Small-3.2-24B-Instruct-2506"
    mock = from_yaml("tests/fixtures/exp_mock_qa.yaml")
    assert served_model_name(mock) == "mock"


def test_api_errors_are_logged_not_persisted(tmp_path):
    from harnesslab.agent.runner import run_experiment
    from harnesslab.store import RolloutStore

    spec = from_yaml("tests/fixtures/exp_mock_qa.yaml", overrides={"k_seeds": 1})
    broken = MockClient(lambda m, s: "Answer: x", fail_times=999)
    s1 = asyncio.run(run_experiment(spec, broken, tmp_path / "r"))
    assert s1.total == s1.ran == s1.api_errors == 6
    assert len(RolloutStore(tmp_path / "r")) == 0          # nothing marked done
    assert RolloutStore(tmp_path / "r").n_failures_logged() == 6

    healthy = MockClient(lambda m, s: "Answer: x")
    s2 = asyncio.run(run_experiment(spec, healthy, tmp_path / "r"))
    assert s2.already_done == 0 and s2.ran == 6 and s2.api_errors == 0
    assert len(RolloutStore(tmp_path / "r")) == 6          # resume retried them all


def test_harmony_vocab_vendored_and_pinned(monkeypatch):
    """Offline gpt-oss serving reads the vendored vocab — it must exist in
    the repo and match harmony's own sha256 pin (runs 1029055/1029364)."""
    import prefetch_models

    monkeypatch.setitem(sys.modules, "openai_harmony", None)  # force sha256-only path
    monkeypatch.delenv("TIKTOKEN_ENCODINGS_BASE", raising=False)
    assert prefetch_models.verify_harmony_vocab() is True
    base = Path(os.environ["TIKTOKEN_ENCODINGS_BASE"])
    assert base == prefetch_models.VENDORED_VOCAB_DIR
    assert (base / "o200k_base.tiktoken").is_file()


def test_harmony_vocab_missing_or_corrupt_is_reported_not_raised(tmp_path, monkeypatch):
    import prefetch_models

    monkeypatch.setenv("TIKTOKEN_ENCODINGS_BASE", str(tmp_path))
    assert prefetch_models.verify_harmony_vocab() is False  # missing
    (tmp_path / "o200k_base.tiktoken").write_text("junk")
    assert prefetch_models.verify_harmony_vocab() is False  # sha256 mismatch


def test_chat_template_kwargs_resolve_and_reach_payload():
    """Per-family template accommodations (Qwen enable_thinking=false, probe
    1034288) flow registry -> spec -> request payload."""
    from harnesslab.client.openai_compat import OpenAICompatClient

    spec = from_yaml(
        "configs/experiments/pilot.yaml", overrides={"model_id": "qwen_3_5_9b"}
    )
    assert spec.chat_template_kwargs == {"enable_thinking": False}
    mistral = from_yaml("configs/experiments/pilot.yaml")
    assert mistral.chat_template_kwargs == {}

    client = OpenAICompatClient(
        "http://x/v1", "m", chat_template_kwargs=spec.chat_template_kwargs
    )
    assert client.chat_template_kwargs == {"enable_thinking": False}


def test_git_state_survives_missing_git_binary(monkeypatch):
    """Compute nodes have no `git` (smoke 1029480 wrote sha=unknown): the
    fallback reads .git/HEAD and never fabricates dirty=False."""
    import subprocess

    from harnesslab import manifest

    real = manifest._git_state(Path(__file__).resolve().parents[1])
    assert real["sha"] != "unknown"

    def no_git(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", no_git)
    fallback = manifest._git_state(Path(__file__).resolve().parents[1])
    assert fallback["sha"] == real["sha"] and fallback["dirty"] is None


def test_sample_indices_deterministic_sorted():
    a = sample_indices(1000, 100, 20260723)
    assert a == sample_indices(1000, 100, 20260723)
    assert a == sorted(a) and len(set(a)) == 100
    assert a != sample_indices(1000, 100, 1)
    assert sample_indices(50, 100, 0) == list(range(50))  # pool smaller than n
