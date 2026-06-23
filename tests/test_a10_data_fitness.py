#!/usr/bin/env python3
"""Tests for the A10 data-fitness flag seed. Hermetic: no warehouse, no network, no analyst repo,
just dict outputs through the grader. Proves the buildable FLAG fires when no fitness check is
stated and when a stated check says the data cannot answer, passes when a stated check is fit, and
that the frontier fitness SCORE reports blocked rather than silently passing.
Run: python3 tests/test_a10_data_fitness.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders.a10_data_fitness import DataFitnessGrader, fitness_score


def test_no_fitness_check_raises_flag():
    g = DataFitnessGrader()
    res = g.grade({"headline": "55.4%"})   # no data_fitness key at all
    assert res.kind == "flag"
    assert res.status == "flag" and res.value is True
    assert "no data-fitness check stated" in res.detail
    # never a correctness score: it is a precondition flag on the question
    assert "frontier" in res.detail


def test_stated_check_cannot_answer_raises_flag():
    g = DataFitnessGrader()
    res = g.grade({"data_fitness": {"fit": False,
                                    "reason": "no checkout funnel at session grain"}})
    assert res.kind == "flag"
    assert res.status == "flag" and res.value is True
    assert "cannot answer" in res.detail
    assert "no checkout funnel at session grain" in res.detail


def test_stated_fit_check_passes():
    g = DataFitnessGrader()
    res = g.grade({"data_fitness": {"fit": True,
                                    "reason": "sessions and checkout funnel exist at session grain"}})
    assert res.kind == "flag"
    assert res.status == "pass" and res.value is False
    assert "fit" in res.detail
    # a flag, never a correctness score
    assert res.family == "judge" and res.truth_basis == "expert" and res.surface == "data"


def test_fitness_score_is_frontier_and_blocked():
    # the SCORE is frontier and not built; it must report blocked, not guess a number
    out = fitness_score({"data_fitness": {"fit": True, "reason": "x"}})
    assert out["status"] == "blocked"
    assert out["value"] is None
    assert "frontier" in out["blocked_on"]


def test_runs_only_at_audit_grade():
    from aievals.graders.base import select_graders
    g = DataFitnessGrader
    assert g.cost_tier == "audit-grade"
    assert select_graders([g], "decision-grade") == []   # below audit-grade: not selected
    assert select_graders([g], "audit-grade") == [g]     # selected at audit-grade


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_a10_data_fitness:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
