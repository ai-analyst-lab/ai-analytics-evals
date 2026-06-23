"""A5 Rubric and judge, the scaffold (family: judge).

Some analysis surfaces have no known answer. SQL executes and numbers reconcile, but whether a
"so what" paragraph is faithful, or whether a recommendation actually follows from the finding,
cannot be checked with a diff. That residue is the expert-judgment regime: a written rubric plus
an LLM judge that scores each output against it.

This module ships the scaffold that part of the framework is allowed to ship now: a rubric format
(behavioral, binary, one pass/fail per axis), the judge-call interface (the judge is injected as a
callable so this stays deterministic and never reaches for a real model here), and the per-axis
score the scorecard reads. What it does NOT ship, and refuses to fake, is the trust: a judge score
is an opinion until it has been measured against human labels (Cohen's or Fleiss' kappa on a
held-out set, then a Rogan-Gladen correction). That calibration is BLOCKED on a labeled set (W4.1).

So the grader returns a per-axis mean as a score (it lives inside the one judge regime, it is never
summed across regimes), but it carries status="flag", not "pass", and a blocked_on that names the
calibration gate. The score is surfaced, never trusted. A calibration stub is present and flagged
required, so nobody mistakes the scaffold for a calibrated instrument.

Source: book/research/V-rubric-judge.md (sections 1, 2, and 4).
"""
from dataclasses import dataclass, field

from aievals.graders.base import Grader, register


# The calibration gate. Carried into every result so the block is in the data, not just the prose.
CALIBRATION_BLOCKED_ON = (
    "W4.1 human-labeled calibration set (two or three annotators, Cohen's or Fleiss' kappa >= 0.8, "
    "then a Rogan-Gladen correction of the judge's pass rate); until the judge is measured against "
    "human labels its score is an opinion, not an instrument"
)


@dataclass
class Axis:
    """One binary criterion of a rubric. Behavioral anchors, not adjectives: each level is defined
    by an observable feature so a stranger could apply it and two humans could agree on it. The
    judge returns one pass/fail per axis, never a 1-to-5 Likert point (the gap between adjacent
    points manufactures disagreement that has nothing to do with the output)."""
    name: str
    pass_anchor: str   # observable feature that earns the point
    fail_anchor: str   # observable feature that loses it


@dataclass
class Rubric:
    """A named set of binary axes for one kind of output. Finer resolution comes from decomposing
    into more binary checks, not from adding scale points."""
    name: str
    axes: list = field(default_factory=list)


# The narrative-quality rubric (faithfulness-shaped). The easier, better-agreed surface: claims
# trace to cited results, the slicing is stated, nothing is asserted the data does not support.
# Meaning-only by construction: an anchor describes a behavior, it never carries a result number.
NARRATIVE_RUBRIC = Rubric(
    name="narrative-quality",
    axes=[
        Axis(
            "headline-supported",
            "the headline claim names the result it rests on, and the direction it asserts matches "
            "that result",
            "the headline asserts a magnitude or direction the cited result does not contain",
        ),
        Axis(
            "slicing-stated",
            "the narrative states the filters, inclusions, and exclusions applied to the data",
            "a figure is reported without saying what was filtered in or out",
        ),
        Axis(
            "date-range-stated",
            "the narrative names the time window of the data it summarizes",
            "the time window is left unstated",
        ),
        Axis(
            "denominator-named",
            "any rate or share names its denominator",
            "a share is reported with no denominator given",
        ),
        Axis(
            "no-unsupported-claims",
            "every claim in the narrative traces to a cited result",
            "the narrative makes an assertion the cited data does not support",
        ),
    ],
)

# The recommendation-quality rubric (the harder, contested surface, from V-rubric-judge.md section
# 5). Same binary discipline applied to the surface that needs it most: two experts who disagree on
# "is this a good recommendation" still tend to agree on "did it name the assumption it breaks on."
RECOMMENDATION_RUBRIC = Rubric(
    name="recommendation-quality",
    axes=[
        Axis(
            "follows-from-finding",
            "the recommended action names the specific finding it rests on, and its direction is "
            "consistent with that finding",
            "the action cites no finding, contradicts it, or is generic best-practice that would "
            "read the same regardless of the data",
        ),
        Axis(
            "alternative-addressed",
            "the recommendation names at least one cheaper or lower-risk alternative and gives a "
            "reason for preferring the chosen one (or states none was cheaper)",
            "the recommendation jumps to the most expensive or highest-risk action with no mention "
            "that a cheaper test exists",
        ),
        Axis(
            "assumption-stated",
            "the recommendation names the load-bearing assumption it would break on",
            "the recommendation is stated as unconditional fact",
        ),
        Axis(
            "risk-named",
            "the recommendation states what could go wrong if acted on and roughly who it affects",
            "only upside is described; the action is presented as costless",
        ),
    ],
)


def calibration_required():
    """Calibration stub, flagged required. BLOCKED: a judge score is not trusted until it has been
    measured against human labels on a held-out set. This returns a blocked marker (not a guess and
    not a silent pass) so any caller that asks "is this judge calibrated yet" gets an honest no, the
    same shape A2c's equivalence judge uses for its parallel W4.1 gate.

    When W4.1 lands the labeled set, this is where the kappa, the judge TPR/TNR, and the
    Rogan-Gladen correction get computed and the marker flips to calibrated."""
    return {
        "status": "blocked",
        "calibrated": False,
        "blocked_on": CALIBRATION_BLOCKED_ON,
        "kappa": None,
        "tpr": None,
        "tnr": None,
    }


@register
class RubricJudgeGrader(Grader):
    """Score an analysis narrative or recommendation against a written rubric using an injected
    judge. Buildable as a scaffold; the score is FLAGGED uncalibrated, never returned as a trusted
    pass."""
    name = "A5-rubric-judge"
    family = "judge"
    truth_basis = "expert"
    surface = "narrative"
    cost_tier = "audit-grade"   # the un-checkable residue, only worth running at the highest stakes
    heavy = True                # audit-only heavy machinery (a model call per axis)

    def grade(self, output, *, intensity="decision-grade", run_type="free-text-with-claims",
              rubric=None, judge=None, **ctx):
        """`output` is the analysis surface judged (a narrative or a recommendation, for example as
        output["narrative"]). `rubric` is a Rubric (defaults to NARRATIVE_RUBRIC). `judge` is the
        injected callable that scores ONE axis: judge(axis, output) returns either a bool/0-1
        verdict or a dict {"verdict": bool, "critique": str} (critique-then-verdict, the more stable
        order). The grader never calls a real model itself; the judge is supplied by the caller."""
        rubric = rubric or NARRATIVE_RUBRIC

        if judge is None:
            return self.result(
                kind="score", status="blocked", value=None,
                blocked_on="no judge callable supplied; A5 needs an injected judge (judge=...)",
                detail="A5 scores against a rubric with an injected judge; none was supplied",
            )
        if not rubric.axes:
            return self.result(
                kind="score", status="not-applicable", value=None,
                detail=f"rubric {rubric.name!r} has no axes to score",
            )

        per_axis = []
        for axis in rubric.axes:
            verdict = judge(axis, output)
            passed = bool(verdict.get("verdict")) if isinstance(verdict, dict) else bool(verdict)
            per_axis.append((axis.name, 1.0 if passed else 0.0))

        mean = sum(score for _, score in per_axis) / len(per_axis)
        breakdown = ", ".join(f"{name}={score}" for name, score in per_axis)

        # A score that lives inside the one judge regime (the mean of binary per-axis checks against
        # a single rubric), never an additive cross-regime number. Status is FLAG, not PASS: the
        # score is surfaced for a human, not trusted as a verdict, because the judge is uncalibrated.
        return self.result(
            kind="score",
            status="flag",
            value=mean,
            detail=(
                f"mean per-axis score {mean} over {len(per_axis)} axes (rubric {rubric.name!r}); "
                f"per-axis: {breakdown}. UNCALIBRATED: this judge has not been measured against "
                "human labels, so the score is an opinion, not an instrument. Do not trust it as a "
                "pass until calibration (W4.1) is run; see calibration_required()."
            ),
            blocked_on=CALIBRATION_BLOCKED_ON,
        )
