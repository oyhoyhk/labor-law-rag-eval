"""Cohen's κ against hand-computed values."""

from eval.calibrate import binary_report, cohen_kappa


def test_kappa_perfect_agreement():
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0


def test_kappa_textbook_example():
    # 50 items: both yes 20, A-yes/B-no 5, A-no/B-yes 10, both no 15 → po=0.7, pe=0.5 → κ=0.4
    a = [True] * 25 + [False] * 25
    b = [True] * 20 + [False] * 5 + [True] * 10 + [False] * 15
    assert cohen_kappa(a, b) == 0.4


def test_kappa_undefined_when_both_constant():
    assert cohen_kappa([True, True], [True, True]) is None


def test_binary_report_precision_recall():
    r = binary_report([True, True, False, False], [True, False, True, False], "unsupported")
    assert r["confusion"] == {"both_pos": 1, "judge_only": 1, "human_only": 1, "both_neg": 1}
    assert r["judge_precision"] == 0.5 and r["judge_recall"] == 0.5
