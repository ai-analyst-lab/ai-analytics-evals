#!/usr/bin/env python3
"""Tests for the A4 triangulation grader (family: self-consistency). Hermetic: no warehouse, no
network, no analyst repo. The grader is pure direction-token logic over output['arms'], so the
tests only build small arm lists. Run: python3 tests/test_a4_triangulation.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders.a4_triangulation import TriangulationGrader, normalize_direction


# ---- direction normalization ---------------------------------------------------------------

def test_normalize_folds_synonyms():
    assert normalize_direction("increase") == "up"
    assert normalize_direction("Decreased") == "down"
    assert normalize_direction("no-effect") == "flat"
    assert normalize_direction("flat") == "flat"
    assert normalize_direction("sideways") is None      # not parseable, not silently a pass
    assert normalize_direction(None) is None


# ---- agreement raises pass, divergence raises the flag -------------------------------------

def test_agreeing_arms_pass():
    g = TriangulationGrader()
    out = {"arms": [
        {"name": "cohort", "direction": "down"},
        {"name": "did", "direction": "decrease"},     # different word, same direction
        {"name": "regression", "direction": "down"},
    ]}
    res = g.grade(out)
    assert res.kind == "flag" and res.status == "pass" and res.value is True
    # never a correctness score: the boundary is stated
    assert "not correctness" in res.detail
    # and the independence caveat is carried, not hidden
    assert "independent" in res.detail


def test_diverging_arms_raise_flag():
    g = TriangulationGrader()
    out = {"arms": [
        {"name": "cohort", "direction": "down"},
        {"name": "did", "direction": "up"},           # diverges
        {"name": "regression", "direction": "flat"},
    ]}
    res = g.grade(out)
    assert res.kind == "flag" and res.status == "flag" and res.value is False
    assert "diverge" in res.detail and "trace" in res.detail


def test_two_arms_agree_and_diverge():
    g = TriangulationGrader()
    assert g.grade({"arms": [{"name": "a", "direction": "up"},
                             {"name": "b", "direction": "positive"}]}).status == "pass"
    assert g.grade({"arms": [{"name": "a", "direction": "up"},
                             {"name": "b", "direction": "down"}]}).status == "flag"


# ---- multi-model arm is partial-until-second-model (Layer 0.5) ------------------------------

def test_single_model_arm_reports_partial_until_second_model():
    g = TriangulationGrader()
    out = {"arms": [
        {"name": "claude-cohort", "direction": "down", "modality": "model", "model": "claude"},
        {"name": "claude-did", "direction": "down", "modality": "model", "model": "claude"},
    ]}
    res = g.grade(out)
    # arms still agree on direction (the method-side math is buildable now)
    assert res.status == "pass"
    # but the multi-model claim is honestly downgraded: no distinct second model wired yet
    assert "partial-until-second-model" in res.detail
    assert "Layer 0.5" in res.detail


def test_two_distinct_models_drops_the_partial_note():
    g = TriangulationGrader()
    out = {"arms": [
        {"name": "claude", "direction": "down", "modality": "model", "model": "claude"},
        {"name": "gpt", "direction": "down", "modality": "model", "model": "gpt"},
    ]}
    res = g.grade(out)
    assert res.status == "pass"
    assert "partial-until-second-model" not in res.detail


# ---- honest not-applicable, never a silent pass --------------------------------------------

def test_no_arms_is_not_applicable():
    g = TriangulationGrader()
    res = g.grade({"arms": []})
    assert res.status == "not-applicable" and res.value is None


def test_too_few_parseable_arms_is_not_applicable():
    g = TriangulationGrader()
    # one parseable, one not: cannot triangulate, must say so rather than pass
    res = g.grade({"arms": [{"name": "a", "direction": "up"},
                            {"name": "b", "direction": "sideways"}]})
    assert res.status == "not-applicable"


def test_registration_metadata():
    g = TriangulationGrader()
    assert g.family == "self-consistency"
    assert g.truth_basis == "self-consistency"
    assert g.surface == "decision"
    assert g.cost_tier == "decision-grade"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_a4_triangulation:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
