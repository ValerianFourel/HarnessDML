"""§8.5 — metrics vs hand-computed fixtures; pass@k/pass∧k identities."""

import math

import pytest

from harnesslab.metrics.calibration import auroc, brier, ece
from harnesslab.metrics.consistency import (
    action_type_dist,
    c_out,
    c_res,
    c_traj_d,
    c_traj_s,
    cv,
    jsd,
    levenshtein,
    normalized_levenshtein,
    pass_all_k,
    pass_at_k,
)


def test_c_out_hand_computed():
    correct = {"a": [True, True], "b": [True, False], "c": [False, False]}
    assert c_out(correct) == pytest.approx((1 + 0 + 1) / 3)


def test_pass_k_identities():
    correct = {"a": [True, True], "b": [True, False], "c": [False, False]}
    assert pass_at_k(correct) == pytest.approx(2 / 3)
    assert pass_all_k(correct) == pytest.approx(1 / 3)
    k1 = {"a": [True], "b": [False]}  # K=1: both collapse to the mean
    assert pass_at_k(k1) == pass_all_k(k1) == 0.5


def test_jsd_hand_computed():
    p, q = {"S": 1.0}, {"S": 0.5, "L": 0.5}
    expected = 0.5 * math.log2(4 / 3) + 0.5 * (0.5 * math.log2(2 / 3) + 0.5 * 1)
    assert jsd(p, q) == pytest.approx(expected)  # ≈ 0.311278
    assert jsd(p, p) == 0.0
    assert jsd({}, {}) == 0.0
    assert jsd({}, q) == 1.0


def test_action_type_dist():
    assert action_type_dist(["S", "S", "L", "A"]) == {"S": 0.5, "L": 0.25, "A": 0.25}
    assert action_type_dist([]) == {}


def test_levenshtein_hand_computed():
    assert levenshtein(["S", "L", "A"], ["S", "A"]) == 1
    assert normalized_levenshtein(["S", "L", "A"], ["S", "A"]) == pytest.approx(1 / 3)
    assert normalized_levenshtein([], []) == 0.0
    assert normalized_levenshtein(["S"], []) == 1.0


def test_c_traj_hand_computed():
    seqs = {"t": [["S", "L", "A"], ["S", "A"]]}
    assert c_traj_s(seqs) == pytest.approx(1 - 1 / 3)
    same = {"t": [["S", "A"], ["S", "A"]]}
    assert c_traj_d(same) == 1.0 and c_traj_s(same) == 1.0


def test_cv_and_c_res_hand_computed():
    assert cv([2.0, 2.0, 2.0]) == 0.0
    assert cv([1.0, 3.0]) == pytest.approx(0.5)  # sd(pop)=1, mean=2
    resources = {"tokens_out": {"t1": [1.0, 3.0]}}
    assert c_res(resources) == pytest.approx(math.exp(-0.5))
    assert math.isnan(c_res({"tokens_out": {"t1": [5.0]}}))  # <2 seeds → undefined


def test_ece_hand_computed():
    assert ece([0.9, 0.6], [True, False]) == pytest.approx(0.5 * 0.1 + 0.5 * 0.6)


def test_auroc_hand_computed():
    assert auroc([0.9, 0.8, 0.1], [True, False, True]) == pytest.approx(0.5)
    assert auroc([0.5, 0.5], [True, False]) == pytest.approx(0.5)  # tie → 0.5
    assert auroc([0.9, 0.1], [True, True]) is None  # degenerate


def test_brier_hand_computed():
    assert brier([1.0, 0.0], [True, False]) == 0.0
    assert brier([0.5, 0.5], [True, False]) == pytest.approx(0.25)
