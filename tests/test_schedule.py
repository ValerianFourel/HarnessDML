"""§8.7 — deterministic seeded interleaving; no config contiguous beyond chance."""

from harnesslab.schedule import interleave, max_run_length


def _queue():
    return [(cfg, task, 0) for cfg in "ABCD" for task in range(25)]


def test_deterministic_given_seed():
    assert interleave(_queue(), 0) == interleave(_queue(), 0)
    assert interleave(_queue(), 0) != interleave(_queue(), 1)


def test_contents_preserved():
    assert sorted(interleave(_queue(), 0)) == sorted(_queue())


def test_interleaving_property():
    labels = [cfg for cfg, _, _ in interleave(_queue(), 0)]
    assert max_run_length(labels) <= 8  # 100 items, 4 configs: far below contiguous 25
    labels = [cfg for cfg, _, _ in interleave(_queue(), 12345)]
    assert max_run_length(labels) <= 8


def test_max_run_length_helper():
    assert max_run_length(["a", "a", "b", "a"]) == 2
    assert max_run_length([]) == 0
