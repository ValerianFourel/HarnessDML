"""Phase-3 provisioning units: fits-check, multi-endpoint client, spec
overrides + task slicing, seeded task sampling."""

import asyncio
import sys
from pathlib import Path

import pytest

from harnesslab.client import MockClient, MultiEndpointClient
from harnesslab.experiment import from_yaml, load_registry
from harnesslab.fits import check_registry, required_gb, serving_mode_for

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
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


def test_sample_indices_deterministic_sorted():
    a = sample_indices(1000, 100, 20260723)
    assert a == sample_indices(1000, 100, 20260723)
    assert a == sorted(a) and len(set(a)) == 100
    assert a != sample_indices(1000, 100, 1)
    assert sample_indices(50, 100, 0) == list(range(50))  # pool smaller than n
