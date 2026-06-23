#!/usr/bin/env python3
"""Tests for A7 Decision justifiability: the no-outcome process flag (buildable now) and the
gated realized-outcome part. Hermetic: no warehouse, no network, no analyst repo. The whole point
is the separation decision quality is not outcome quality, so these tests prove the process flag
works, the outcome part reports blocked rather than guessing a number, and importing this module
adds NO member to the outcome-lookup family. Run: python3 tests/test_a7_decision.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders.a7_decision import (
    DecisionGrader, evaluate_decision_quality, DECISION_ELEMENTS,
)
from aievals.graders.base import by_family

# A recommendation whose six elements all hold (a sound call on the evidence).
SOUND = {
    "recommendation": "Keep the gate at level 30; the move to 40 lowered retention.",
    "rubric": {e: True for e in DECISION_ELEMENTS},
    "rests_on_validated_analysis": True,
}
# Same prose, but the chain from number to action does not follow (reasoning fails).
DOES_NOT_FOLLOW = {
    "recommendation": "Move the gate to level 40 to boost retention.",
    "rubric": {**{e: True for e in DECISION_ELEMENTS}, "reasoning": False},
    "rests_on_validated_analysis": True,
}


# ---- the no-outcome process flag (buildable now) -------------------------------------------

def test_a7_passes_a_sound_recommendation():
    g = DecisionGrader()
    res = g.grade(SOUND)
    assert res.kind == "flag" and res.status == "pass" and res.value is True
    # never a claim the decision was right: process quality, not outcome quality
    assert "not outcome quality" in res.detail
    assert g.family == "judge" and g.cost_tier == "operational"


def test_a7_flags_recommendation_that_does_not_follow():
    g = DecisionGrader()
    res = g.grade(DOES_NOT_FOLLOW)
    assert res.kind == "flag" and res.status == "flag" and res.value is False
    assert "reasoning" in res.detail  # the weakest link is named


def test_a7_g37_guard_knocks_down_recommendation_on_broken_analysis():
    # Every rubric element reads true, but the recommendation rests on an analysis that failed its
    # own checks. A fluent recommendation on a broken number must score down, not up (G37).
    fluent_but_broken = {
        "recommendation": "Ship it; the lift is clear.",
        "rubric": {e: True for e in DECISION_ELEMENTS},
        "rests_on_validated_analysis": False,
    }
    res = DecisionGrader().grade(fluent_but_broken)
    assert res.status == "flag" and res.value is False
    assert "information" in res.detail


def test_a7_not_applicable_without_a_recommendation():
    assert evaluate_decision_quality({"number": "55.4%"}) is None
    res = DecisionGrader().grade({"number": "55.4%"})
    assert res.status == "not-applicable" and res.value is None


def test_a7_never_emits_a_number_in_the_flag():
    # the value is a boolean soundness verdict, never a score on [0,1]
    for out in (SOUND, DOES_NOT_FOLLOW):
        res = DecisionGrader().grade(out)
        assert isinstance(res.value, bool)


# ---- the gated realized-outcome part (Regime E) --------------------------------------------

def test_a7_realized_outcome_reports_blocked_not_a_number():
    res = DecisionGrader().score_realized_outcome(
        recommendation="keep gate 30", outcome_pair=None)
    assert res.status == "blocked"
    assert res.value is None                      # never a number
    assert res.blocked_on == "F.1 reconciled outcome pairs"
    assert res.family == "outcome-lookup"         # it speaks for the outcome regime
    assert res.truth_basis == "outcome"


# ---- the honest registry: outcome-lookup stays a registered-but-empty slot -----------------

def test_a7_does_not_populate_the_outcome_lookup_family():
    # importing A7 registers ONLY its judge-flag part; the outcome-lookup family must stay empty
    # until F.1 lands the reconciled pairs, reported empty rather than green.
    assert by_family("outcome-lookup") == []
    judge_names = [g.name for g in by_family("judge")]
    assert "A7-decision" in judge_names           # the buildable part is registered, in judge


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_a7_decision:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
