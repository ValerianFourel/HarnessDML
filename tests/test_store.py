"""§8.6 — store idempotency; partial-line corruption survives resume."""

import json

from harnesslab.store import RolloutStore, make_rollout_key

CELL = {"model_id": "m", "benchmark": "hotpotqa", "band": "easy",
        "config_id": "T", "ordering_id": "o1", "template_id": "t1", "temp": 0.1}


def rec(task_id, seed):
    return {"rollout_key": make_rollout_key(CELL, task_id, seed),
            "task_id": task_id, "seed": seed}


def test_key_is_deterministic_and_distinct():
    assert make_rollout_key(CELL, "t1", 0) == make_rollout_key(CELL, "t1", 0)
    assert make_rollout_key(CELL, "t1", 0) != make_rollout_key(CELL, "t1", 1)
    assert make_rollout_key(CELL, "t1", 0) != make_rollout_key({**CELL, "config_id": "P"}, "t1", 0)


def test_append_reload_and_idempotency(tmp_path):
    store = RolloutStore(tmp_path)
    store.append(rec("a", 0))
    store.append(rec("a", 0))  # duplicate append is a no-op
    store.append(rec("b", 0))
    assert len(store) == 2
    assert len(open(store.path).readlines()) == 2

    reopened = RolloutStore(tmp_path)
    assert len(reopened) == 2
    assert reopened.is_done(rec("a", 0)["rollout_key"])


def test_partial_line_corruption_survives_resume(tmp_path):
    store = RolloutStore(tmp_path)
    store.append(rec("a", 0))
    with open(store.path, "a") as f:  # killed job mid-write
        f.write(json.dumps(rec("b", 0))[:17])

    recovered = RolloutStore(tmp_path)
    assert len(recovered) == 1 and recovered.n_corrupt == 1
    assert not recovered.is_done(rec("b", 0)["rollout_key"])  # b re-runs

    recovered.append(rec("b", 0))
    assert len(recovered) == 2
    assert sum(1 for _ in recovered.records()) == 2  # corrupt line skipped
