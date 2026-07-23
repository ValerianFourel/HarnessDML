"""Run-manifest provenance: id format and required fields."""

import json
import re
from datetime import datetime, timezone

from halcausal.io import manifest


def test_run_id_format():
    rid = manifest.new_run_id(datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc))
    assert re.fullmatch(r"20260723T120000Z-[0-9a-f]{8}", rid)


def test_manifest_contents(tmp_path):
    config = tmp_path / "estimand.yaml"
    config.write_text("estimand_id: test\n")

    rid = manifest.new_run_id()
    out = manifest.write_manifest(
        rid,
        out_dir=tmp_path / "manifests",
        config_path=config,
        seeds={"global": 20260723},
        input_checksums={"a.zip": "0" * 64},
        counts={"rollouts": 123},
    )
    assert out.name == f"{rid}.json"

    m = json.loads(out.read_text())
    assert m["run_id"] == rid
    assert re.fullmatch(r"[0-9a-f]{40}", m["git"]["sha"])
    assert re.fullmatch(r"[0-9a-f]{64}", m["freeze_digest"])
    assert re.fullmatch(r"[0-9a-f]{64}", m["config"]["sha256"])
    assert m["seeds"] == {"global": 20260723}
    assert m["counts"]["rollouts"] == 123
    assert m["package_versions"]["doubleml"] is not None
