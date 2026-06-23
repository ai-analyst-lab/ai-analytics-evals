#!/usr/bin/env python3
"""Tests for the A6 methodology justifiability grader. Hermetic: no warehouse, no network, no
analyst repo. The grader is a pure shape over a small question-type to method-family map, so the
tests are plain dicts. They prove the FLAG fires on a wrong-type method and on a missing estimand
or assumption, passes only when all three conditions hold, and that the "is the method right"
correctness score is honestly reported as frontier/blocked. Run: python3 tests/test_a6_methodology.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders.a6_methodology import (
    MethodologyGrader, method_family, type_matches, method_correctness_score,
)

# A fully justified causal analysis: causal question, a causal method, estimand and assumption named.
GOOD_CAUSAL = {
    "question_type": "causal",
    "method": {
        "type": "did",
        "estimand": "ATT on delivered-fast adopters",
        "identifying_assumption": "parallel trends in the pre-period",
    },
}


# ---- the map helpers -----------------------------------------------------------------------

def test_method_family_classifies_and_normalizes():
    assert method_family("did") == "causal"
    assert method_family("Difference in Differences") == "causal"   # normalized
    assert method_family("before-and-after") == "descriptive"
    assert method_family("funnel_decomposition") == "diagnostic"
    assert method_family("forecasting") == "predictive"
    assert method_family("made-up-method") is None                  # unknown, not a guess


def test_type_matches_only_within_defensible_set():
    assert type_matches("causal", "did")
    assert not type_matches("causal", "before-and-after")          # descriptive for a causal Q
    assert type_matches("descriptive", "aggregation")
    assert not type_matches("causal", "made-up-method")            # unknown is not a match
    assert not type_matches(None, "did")


# ---- the grader: flag behavior -------------------------------------------------------------

def test_pass_when_method_fits_and_is_documented():
    res = MethodologyGrader().grade(GOOD_CAUSAL)
    assert res.kind == "flag"            # never a score, always a flag
    assert res.status == "pass" and res.value is True
    assert "not correctness" in res.detail
    assert MethodologyGrader.cost_tier == "operational"
    assert MethodologyGrader.family == "judge" and MethodologyGrader.truth_basis == "expert"


def test_wrong_type_method_raises_the_flag():
    # a before-and-after (descriptive pre/post) for a causal question is the wrong type
    out = {
        "question_type": "causal",
        "method": {
            "type": "before-and-after",
            "estimand": "the drop in conversion",
            "identifying_assumption": "nothing else changed",
        },
    }
    res = MethodologyGrader().grade(out)
    assert res.kind == "flag" and res.status == "flag" and res.value is False
    assert "wrong-type" in res.detail


def test_missing_estimand_raises_the_flag():
    out = {
        "question_type": "causal",
        "method": {"type": "did", "identifying_assumption": "parallel trends"},
    }
    res = MethodologyGrader().grade(out)
    assert res.status == "flag" and res.value is False
    assert "estimand not stated" in res.detail


def test_missing_assumption_raises_the_flag():
    out = {
        "question_type": "causal",
        "method": {"type": "did", "estimand": "ATT on adopters"},
    }
    res = MethodologyGrader().grade(out)
    assert res.status == "flag" and res.value is False
    assert "identifying assumption not named" in res.detail


def test_unstated_method_flags_not_silently_passes():
    res = MethodologyGrader().grade({"question_type": "causal"})
    assert res.status == "flag" and res.value is False
    assert "method not stated" in res.detail


def test_not_applicable_when_nothing_to_assess():
    res = MethodologyGrader().grade({})
    assert res.status == "not-applicable" and res.value is None


# ---- the frontier correctness score is blocked, not faked ----------------------------------

def test_method_correctness_score_is_frontier_blocked():
    sc = method_correctness_score(GOOD_CAUSAL["method"], "causal")
    assert sc["status"] == "blocked" and sc["score"] is None
    assert sc["blocked_on"]   # carries a reason


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_a6_methodology:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
