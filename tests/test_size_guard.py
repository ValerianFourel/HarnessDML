"""Phase 0: pre-commit size guard (§8.8 will later exercise it end-to-end)."""

import importlib.machinery
import importlib.util
from pathlib import Path

_HOOK = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "pre-commit"
_loader = importlib.machinery.SourceFileLoader("pre_commit_guard", str(_HOOK))
_spec = importlib.util.spec_from_loader("pre_commit_guard", _loader)
guard = importlib.util.module_from_spec(_spec)
_loader.exec_module(guard)


def test_rollout_jsonl_rejected_anywhere():
    assert guard.violations([("scratch/exp1/rollouts/part-000.jsonl", 10)])
    assert guard.violations([("rollouts/x.jsonl", 10)])


def test_non_rollout_artifacts_pass():
    assert guard.violations([
        ("results/mvp_grid/panel.parquet", 5_000_000),
        ("results/mvp_grid/cell_metrics.parquet", 100_000),
        ("results/mvp_grid/manifest_index.json", 2_000),
    ]) == []


def test_total_over_20mb_rejected():
    problems = guard.violations([("results/a.parquet", guard.MAX_TOTAL_BYTES + 1)])
    assert len(problems) == 1 and "20 MB" in problems[0]


def test_both_rules_report_independently():
    problems = guard.violations([("x/rollouts/a.jsonl", guard.MAX_TOTAL_BYTES + 1)])
    assert len(problems) == 2


def test_git_end_to_end_rejects_oversized_commit(tmp_path):
    """§8.8 — a real `git commit` with 21 MB staged is rejected by the hook."""
    import subprocess

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True
        )

    git("init", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    git("config", "core.hooksPath", str(_HOOK.parent))

    (tmp_path / "big.bin").write_bytes(b"\0" * (21 * 2**20))
    git("add", "big.bin")
    res = git("commit", "-m", "should fail")
    assert res.returncode != 0 and "SIZE GUARD" in res.stderr

    git("reset")
    (tmp_path / "small.txt").write_text("ok")
    git("add", "small.txt")
    assert git("commit", "-m", "fine").returncode == 0
