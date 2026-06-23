#!/usr/bin/env python3
"""Tests for the A5 rubric/judge scaffold. Hermetic: the judge is injected as a FAKE callable, so
no model and no network are touched. Proves the scaffold works (the judge runs, per-axis scores
roll into a mean) AND stays honest (the result is flagged uncalibrated, never a trusted pass, and
the calibration stub reports blocked). Run: python3 tests/test_a5_rubric_judge.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders.a5_rubric_judge import (
    RubricJudgeGrader, Axis, Rubric, NARRATIVE_RUBRIC, RECOMMENDATION_RUBRIC,
    calibration_required, CALIBRATION_BLOCKED_ON,
)
from aievals.graders.base import select_graders


def _fake_judge(passing_axes):
    """A deterministic stand-in for the LLM judge. Passes exactly the named axes, fails the rest,
    and returns critique-then-verdict (the shape the real judge uses)."""
    def judge(axis, output):
        return {"critique": f"checked {axis.name} against the output", "verdict": axis.name in passing_axes}
    return judge


SAMPLE = {"narrative": "retention held over the period for the active cohort"}


# ---- the judge runs and returns a per-axis score -------------------------------------------

def test_judge_runs_and_scores_every_axis():
    g = RubricJudgeGrader()
    all_axes = {a.name for a in NARRATIVE_RUBRIC.axes}
    res = g.grade(SAMPLE, judge=_fake_judge(all_axes))
    assert res.kind == "score"
    assert res.value == 1.0                      # every axis passed -> mean 1.0
    # the per-axis breakdown is surfaced, every axis named
    for a in NARRATIVE_RUBRIC.axes:
        assert a.name in res.detail


def test_partial_pass_gives_fractional_mean():
    g = RubricJudgeGrader()
    axes = NARRATIVE_RUBRIC.axes
    passing = {axes[0].name, axes[1].name}       # 2 of N pass
    res = g.grade(SAMPLE, judge=_fake_judge(passing))
    expected = len(passing) / len(axes)          # computed, not hardcoded
    assert res.value == expected
    assert 0.0 < res.value < 1.0


def test_recommendation_rubric_also_scores():
    g = RubricJudgeGrader()
    res = g.grade({"recommendation": "do X"}, rubric=RECOMMENDATION_RUBRIC, judge=_fake_judge(set()))
    assert res.value == 0.0                       # nothing passed
    assert "recommendation-quality" in res.detail


# ---- the result is flagged uncalibrated, NOT a trusted pass --------------------------------

def test_score_is_flagged_uncalibrated_not_a_pass():
    g = RubricJudgeGrader()
    res = g.grade(SAMPLE, judge=_fake_judge({a.name for a in NARRATIVE_RUBRIC.axes}))
    # even with a perfect 1.0, the verdict is a FLAG, never "pass": the judge is uncalibrated
    assert res.status == "flag"
    assert res.status != "pass"
    assert res.blocked_on == CALIBRATION_BLOCKED_ON
    assert "W4.1" in res.blocked_on
    assert "UNCALIBRATED" in res.detail and "Do not trust" in res.detail


# ---- the calibration stub is present and flagged required ----------------------------------

def test_calibration_stub_reports_blocked():
    c = calibration_required()
    assert c["status"] == "blocked"
    assert c["calibrated"] is False
    assert "W4.1" in c["blocked_on"]
    assert c["kappa"] is None and c["tpr"] is None and c["tnr"] is None


# ---- honest failure modes ------------------------------------------------------------------

def test_blocks_when_no_judge_supplied():
    res = RubricJudgeGrader().grade(SAMPLE, judge=None)
    assert res.status == "blocked"
    assert "judge" in res.blocked_on
    assert res.value is None


def test_not_applicable_on_empty_rubric():
    res = RubricJudgeGrader().grade(SAMPLE, rubric=Rubric(name="empty", axes=[]),
                                    judge=_fake_judge(set()))
    assert res.status == "not-applicable"
    assert res.value is None


# ---- selection: heavy, audit-grade only ----------------------------------------------------

def test_heavy_audit_only_selection():
    g = RubricJudgeGrader
    assert g.heavy is True and g.cost_tier == "audit-grade"
    assert select_graders([g], "decision-grade") == []      # heavy, excluded below audit-grade
    assert select_graders([g], "audit-grade") == [g]        # included at audit-grade


# ---- the rubric is meaning-only (no result number baked into an anchor) ---------------------

def test_rubric_anchors_carry_no_result_numbers():
    for rubric in (NARRATIVE_RUBRIC, RECOMMENDATION_RUBRIC):
        for axis in rubric.axes:
            blob = axis.pass_anchor + axis.fail_anchor + axis.name
            assert not any(ch.isdigit() for ch in blob), f"{axis.name} leaks a literal number"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_a5_rubric_judge:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
