"""Per-slice progress: each spec's own denominator, in-scope numerator.

The bugs these pin down are the ones that made a raw `wc -l` dashboard lie:
a complete 4-config thin arm reading "13%" against the 32-config grid target,
and a census store reading "147%" because pre-cap orphans inflate the count.
"""

import json

import pytest

from harnesslab import experiment, progress


def _spec(name, bench="gsm8k"):
    return experiment.from_yaml(
        progress.spec_path(name),
        overrides={"benchmark": bench, "tasks_file": f"configs/tasks/{bench}.jsonl"},
    )


def test_target_uses_the_specs_own_config_count():
    """32-config grid and 4-config thin arm share a benchmark, not a target."""
    grid, thin = _spec("mvp_grid"), _spec("mvp_thin_gsm8k")
    n_tasks = len(progress.in_scope_ids(grid, "gsm8k"))
    assert progress.slice_target(grid, "gsm8k") == 32 * n_tasks * 5
    assert progress.slice_target(thin, "gsm8k") == 4 * n_tasks * 5


def test_n_tasks_caps_the_denominator():
    """HotpotQA's 7405-task pool is capped to 3000 by mvp_grid's n_tasks."""
    grid = _spec("mvp_grid", "hotpotqa")
    assert grid.n_tasks == 3000
    assert len(progress.in_scope_ids(grid, "hotpotqa")) == 3000
    assert progress.slice_target(grid, "hotpotqa") == 32 * 3000 * 5


def _row(task_id, seed, config_id="T", padded=""):
    return {"task_id": task_id, "seed": seed, "config_id": config_id,
            "ordering_id": "o1", "template_id": "t1", "padded_components": padded,
            "temp": 0.1, "rollout_key": f"{config_id}-{task_id}-{seed}-{padded}"}


def test_scan_separates_orphans_and_duplicates(tmp_path):
    store = tmp_path / "rollouts.jsonl"
    rows = [
        _row("in-1", 0),
        _row("in-1", 1),
        _row("in-1", 0, padded=""),          # same (cell, task, seed) -> duplicate
        _row("out-9", 0),                    # task outside the capped list
    ]
    store.write_text("".join(json.dumps(r) + "\n" for r in rows) + "{bad json\n")
    s = progress.scan_store(store, keep={"in-1"})
    assert s == {"lines": 5, "in_scope": 3, "unique": 2,
                 "orphans": 1, "dupes": 1, "corrupt": 1}


def test_a_row_missing_padded_components_is_the_same_unit_of_work(tmp_path):
    """The re-key duplicate (ADR 22): pre-padding rows have no
    `padded_components` at all, post-padding rows have ''. aggregate treats
    them as equal, so progress must too — otherwise duplicates count as 0 and
    unique work runs past the target."""
    old = _row("a", 0)
    old.pop("padded_components")
    new = _row("a", 0, padded="")
    assert progress.unit_key(old) == progress.unit_key(new)

    store = tmp_path / "rollouts.jsonl"
    store.write_text(json.dumps(old) + "\n" + json.dumps(new) + "\n")
    s = progress.scan_store(store, keep={"a"})
    assert (s["in_scope"], s["unique"], s["dupes"]) == (2, 1, 1)


def test_scan_without_a_task_filter_keeps_everything(tmp_path):
    store = tmp_path / "rollouts.jsonl"
    store.write_text(json.dumps(_row("a", 0)) + "\n" + json.dumps(_row("b", 0)) + "\n")
    s = progress.scan_store(store, keep=None)
    assert (s["in_scope"], s["unique"], s["orphans"]) == (2, 2, 0)


def test_walk_reads_target_from_the_store_path(tmp_path):
    d = tmp_path / "mvp_thin_gsm8k" / "rollouts_mistral_small_3_2_24b_gsm8k"
    d.mkdir(parents=True)
    (d / "rollouts.jsonl").write_text(json.dumps(_row("a", 0)) + "\n")
    (d / "failures.jsonl").write_text('{"api_error": 1}\n')
    [row] = progress.walk(tmp_path)
    assert (row.exp, row.model, row.bench) == (
        "mvp_thin_gsm8k", "mistral_small_3_2_24b", "gsm8k")
    assert row.target == progress.slice_target(_spec("mvp_thin_gsm8k"), "gsm8k")
    assert row.lines == 1 and row.failures == 1 and row.status == "PARTIAL"


def test_unknown_experiment_dir_has_no_target_but_still_counts(tmp_path):
    d = tmp_path / "not_an_experiment" / "rollouts_m_gsm8k"
    d.mkdir(parents=True)
    (d / "rollouts.jsonl").write_text(json.dumps(_row("a", 0)) + "\n")
    [row] = progress.walk(tmp_path)
    assert row.target is None and row.status == "no-spec" and row.lines == 1


def test_orphans_make_a_shallow_count_claim_a_slice_is_finished(tmp_path):
    """The 147%-of-target lie: raw lines run past the target while real work
    is still pending, because out-of-scope tasks inflate the count."""
    thin = _spec("mvp_thin_gsm8k")
    ids = sorted(progress.in_scope_ids(thin, "gsm8k"))
    target = progress.slice_target(thin, "gsm8k")
    rows = [_row(t, s, c) for c in ("BARE", "T", "T+SR+R", "P+T+M+SR+R")
            for t in ids for s in range(5)]
    assert len(rows) == target
    rows.pop()                                          # one in-scope rollout short
    rows += [_row(f"orphan-{i}", 0) for i in range(3)]   # out of scope: must not count

    d = tmp_path / "mvp_thin_gsm8k" / "rollouts_m_gsm8k"
    d.mkdir(parents=True)
    (d / "rollouts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))

    [shallow] = progress.walk(tmp_path)
    assert shallow.lines == target + 2 and shallow.status == "DONE?"

    [deep] = progress.walk(tmp_path, deep=True)
    assert deep.unique == target - 1 and deep.orphans == 3
    assert deep.status == "ORPHANS?" and deep.remaining == 1


def test_deep_walk_marks_a_genuinely_finished_slice_done(tmp_path):
    thin = _spec("mvp_thin_gsm8k")
    ids = sorted(progress.in_scope_ids(thin, "gsm8k"))
    rows = [_row(t, s, c) for c in ("BARE", "T", "T+SR+R", "P+T+M+SR+R")
            for t in ids for s in range(5)]
    d = tmp_path / "mvp_thin_gsm8k" / "rollouts_m_gsm8k"
    d.mkdir(parents=True)
    (d / "rollouts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))

    [deep] = progress.walk(tmp_path, deep=True)
    assert deep.status == "DONE" and deep.remaining == 0 and deep.orphans == 0


def test_auto_scope_reads_the_cap_from_the_store_path(tmp_path):
    """Harvesting HotpotQA unfiltered ships 4405 tasks' worth of orphans; the
    cap must come from the path, not from the operator remembering it."""
    store = tmp_path / "mvp_grid" / "rollouts_qwen_3_5_9b_hotpotqa"
    ids, why = progress.auto_scope(store)
    assert len(ids) == 3000 and "n_tasks=3000" in why

    store = tmp_path / "mvp_grid" / "rollouts_qwen_3_5_9b_math"
    ids, _ = progress.auto_scope(store)          # pool below the cap: no-op
    assert len(ids) == len(progress.load_tasks(progress.ROOT / "configs/tasks/math.jsonl"))

    ids, why = progress.auto_scope(tmp_path / "nope" / "rollouts_m_gsm8k")
    assert ids is None and "no spec" in why


def test_deep_walk_caches_unchanged_stores_and_reruns_changed_ones(tmp_path):
    """A finished slice hasn't changed in days; re-reading it every time is
    what made --deep take minutes. Cache on (size, mtime, scope)."""
    d = tmp_path / "mvp_thin_gsm8k" / "rollouts_m_gsm8k"
    d.mkdir(parents=True)
    store = d / "rollouts.jsonl"
    ids = sorted(progress.in_scope_ids(_spec("mvp_thin_gsm8k"), "gsm8k"))[:3]
    store.write_text("".join(json.dumps(_row(t, 0)) + "\n" for t in ids))

    [first] = progress.walk(tmp_path, deep=True)
    assert first.unique == 3
    assert (tmp_path / progress.CACHE_NAME).exists()

    # corrupt the store's CONTENT without touching size/mtime -> a cached walk
    # must return the old numbers, proving it did not re-read
    cache = json.loads((tmp_path / progress.CACHE_NAME).read_text())
    key = next(iter(cache))
    cache[key]["unique"] = 99
    (tmp_path / progress.CACHE_NAME).write_text(json.dumps(cache))
    [cached] = progress.walk(tmp_path, deep=True)
    assert cached.unique == 99                     # served from cache
    [fresh] = progress.walk(tmp_path, deep=True, use_cache=False)
    assert fresh.unique == 3                       # --fresh bypasses it

    # appending changes size -> the entry is invalid and the store is rescanned
    with open(store, "a") as f:
        f.write(json.dumps(_row(ids[0], 1)) + "\n")
    [grown] = progress.walk(tmp_path, deep=True)
    assert grown.unique == 4


def test_summary_never_counts_a_slice_past_its_target():
    """Orphan-inflated slices must not push the census total above 100%."""
    rows = [
        progress.SliceProgress(exp="mvp_grid", model="m", bench="hotpotqa", path=None,
                               lines=700_000, target=480_000),          # orphan-inflated
        progress.SliceProgress(exp="mvp_grid", model="m", bench="math", path=None,
                               lines=20_960, target=41_920),            # half done
        progress.SliceProgress(exp="pilot", model="m", bench="math", path=None,
                               lines=160, target=160),                  # not census
    ]
    text = progress.summarize(rows)
    assert "500,960" in text and "521,920" in text   # 480,000 capped + 20,960
    assert "96.0%" in text


def test_summary_denominator_matches_the_rulings_not_the_stores():
    """A gated band whose chain hasn't produced a first rollout has no store;
    counting only stores shrank the target and inflated the percentage."""
    rows = [progress.SliceProgress(exp="mvp_grid", model="m", bench="math", path=None,
                                   lines=41_920, target=41_920)]
    gates = {"models": {"m": {"math": {"status": "census"},
                              "gsm8k": {"status": "census"}}}}   # gsm8k: no store yet
    assert "100.0%" in progress.summarize(rows)                  # store-only view
    text = progress.summarize(rows, gates=gates)
    assert f"{41_920 + 32 * 1319 * 5:,}" in text                 # math + unstarted gsm8k
    assert "100.0%" not in text


def test_roster_covers_every_registry_model_including_storeless_ones():
    """A model that was probed but never piloted leaves no store, so a
    store-driven view drops it silently — the roster must still list it."""
    registry = experiment.load_registry()
    row = progress.SliceProgress(exp="mvp_grid", model="qwen_3_5_9b", bench="math",
                                 path=None, lines=41_920, target=41_920)
    text = progress.roster([row], progress.load_gates(), registry)
    for model in registry:
        assert model in text, f"{model} missing from the roster"
    assert "BLK" in text        # deepseek_v4_flash: cannot serve on this stack
    assert "BRDG" in text       # llama_3_1_8b: bridge arm only
    assert "ALL GATED MODELS" in text


def test_ruling_target_exists_without_a_store():
    """The outstanding work of a gated-but-never-run model is knowable."""
    assert progress.ruling_target("census", "math") == 32 * 262 * 5
    assert progress.ruling_target("thin", "gsm8k") == 4 * 1319 * 5
    assert progress.ruling_target("dropped", "math") == 0


def test_gaps_lists_gated_slices_with_no_store():
    gates = {"models": {
        "m_done": {"gsm8k": {"status": "census"}},
        "m_missing": {"math": {"status": "census"}},
        "m_dropped": {"math": {"status": "dropped"}},
    }}
    thin = _spec("mvp_thin_gsm8k")
    row = progress.SliceProgress(exp="mvp_grid", model="m_done", bench="gsm8k",
                                 path=None, lines=1,
                                 target=progress.slice_target(thin, "gsm8k"), unique=1)
    out = progress.gaps([row], gates)
    assert {(g["model"], g["bench"], g["state"]) for g in out} == {
        ("m_missing", "math", "NO STORE"), ("m_done", "gsm8k", "PARTIAL")}


def test_committed_gates_file_is_valid():
    gates = progress.load_gates()
    known = set(experiment.load_registry())
    allowed = {"census", "thin", "dropped", "bridge_only", "pending_gate",
               "unprobed", "blocked", "out_of_scope"}
    for model, benches in gates["models"].items():
        assert model in known, f"{model} is not in configs/models.yaml"
        for bench, ruling in benches.items():
            assert bench in ("hotpotqa", "musique", "gsm8k", "math")
            assert ruling["status"] in allowed, f"{model}/{bench}: {ruling['status']}"
    # a registry model with no ruling is an undecided model, not a documented one
    assert set(known) == set(gates["models"]), \
        f"no gate ruling for: {set(known) - set(gates['models'])}"


def test_an_unfinished_slice_nobody_is_writing_reads_as_stalled():
    """The ministral/gsm8k failure: the chain ran out, the slice sat at 62.7%
    for hours, and every view called it PARTIAL — same as healthy progress."""
    live = progress.SliceProgress(exp="mvp_grid", model="m", bench="gsm8k", path=None,
                                  lines=100, target=1000, age_s=60)
    idle = progress.SliceProgress(exp="mvp_grid", model="m", bench="gsm8k", path=None,
                                  lines=100, target=1000, age_s=9 * 3600)
    assert live.status == "PARTIAL" and idle.status == "STALL?"
    [gap] = progress.gaps([idle], {"models": {"m": {"gsm8k": {"status": "census"}}}})
    assert "chain exhausted?" in gap["note"]


@pytest.mark.parametrize("bench", ["hotpotqa", "musique", "gsm8k", "math"])
def test_every_census_ruling_has_a_reachable_target(bench):
    """A gate ruling nobody can turn into a job is a documentation bug."""
    grid = _spec("mvp_grid", bench)
    assert progress.slice_target(grid, bench) > 0
