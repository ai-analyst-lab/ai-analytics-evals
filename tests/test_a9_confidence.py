#!/usr/bin/env python3
"""Tests for the A9 confidence-tier grader. Fully hermetic: no warehouse, no network, no analyst
repo. The tier is derived from deterministic provenance inputs, and the central proof is that the
model's own self-reported confidence is ignored. Run: python3 tests/test_a9_confidence.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders.a9_confidence import (
    ConfidenceTierGrader, deterministic_tier, TIERS,
)


# ---- the deterministic derivation ----------------------------------------------------------

def test_tier_is_computed_from_the_three_legs():
    # all legs strong -> high
    assert deterministic_tier("certified", "validated", 3) == "high"
    # all legs weak -> low
    assert deterministic_tier("raw", "unvalidated", 1) == "low"
    # all legs middle -> medium
    assert deterministic_tier("modeled", "partial", 2) == "medium"


def test_weakest_link_bounds_the_tier():
    # a governed, validated number that rests on a single run is still a single-run number
    assert deterministic_tier("certified", "validated", 1) == "low"
    # one weak leg drags an otherwise strong chain down to its level
    assert deterministic_tier("certified", "unvalidated", 3) == "low"
    assert deterministic_tier("modeled", "validated", 3) == "medium"


def test_unknown_and_missing_inputs_fall_to_weakest():
    # an unrecognized source/validation is not evidence of a strong one
    assert deterministic_tier("something-odd", "validated", 3) == "low"
    assert deterministic_tier("certified", "who-knows", 3) == "low"
    # missing legs and unparseable run counts fall to the weakest rung
    assert deterministic_tier(None, None, None) == "low"
    assert deterministic_tier("certified", "validated", "lots") == "low"


# ---- the load-bearing property: the model self-report is IGNORED ----------------------------

def test_model_confidence_does_not_change_the_tier():
    g = ConfidenceTierGrader()
    base = {"source_tier": "modeled", "validation_status": "partial", "run_count": 2}
    timid = g.grade({**base, "model_confidence": 0.01})
    cocky = g.grade({**base, "model_confidence": 0.99})
    # the self-report swings from near-zero to near-one; the tier must not move
    assert timid.value == cocky.value == "medium"
    # and it matches the tier with no self-report present at all
    assert g.grade(base).value == "medium"
    # the detail is honest that the self-report was seen and discarded
    assert "ignored by design" in cocky.detail


# ---- the grader shape and honest labels ----------------------------------------------------

def test_returns_a_flag_label_never_a_number():
    g = ConfidenceTierGrader()
    res = g.grade({"source_tier": "certified", "validation_status": "validated", "run_count": 3})
    assert res.kind == "flag"               # surfaced, never summed into a correctness number
    assert res.status == "flag"
    assert isinstance(res.value, str) and res.value in TIERS  # an ordinal label, not a number
    assert res.family == "computable" and res.truth_basis == "computable"
    assert res.surface == "confidence" and g.cost_tier == "decision-grade"
    # frontier honesty: it says it is a label, not a confidence number, and not the self-report
    assert "not a confidence number" in res.detail
    assert "never from the model self-report" in res.detail


def test_no_provenance_reports_not_applicable_not_a_pass():
    g = ConfidenceTierGrader()
    # not a dict at all
    assert g.grade("85% confident").status == "not-applicable"
    # a dict with no provenance legs (a stray self-report is not provenance)
    res = g.grade({"model_confidence": 0.95})
    assert res.status == "not-applicable" and res.value is None


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_a9_confidence:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
