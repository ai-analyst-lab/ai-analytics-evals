"""A7 Decision justifiability (family: judge flag), plus a gated realized-outcome part.

The hardest tier to validate honestly, because of one separation the whole chapter is built to
hold: decision quality is not outcome quality. A good outcome is not proof of a good decision
(Annie Duke's resulting fallacy), so this grader refuses to launder a lucky result into a sound
call. It splits the check into two layers, and the order is load-bearing.

The DEFAULT layer, buildable now and tested here, evaluates the recommendation on its PROCESS,
with no outcome at all: would a good analyst make this call on this evidence? It applies the
six-element decision-quality rubric (Spetzler) on the weakest-link rule (a decision is only as
strong as its weakest element), and returns a FLAG (sound or not), never a correctness score.
The flag fires when the chain from number to action does not follow, or when the recommendation
rests on an analysis that did not pass its own checks (the G37 rubric-as-target guard: a fluent
recommendation resting on a broken number must score down, not up). This is a deterministic
structural application of the rubric, the buildable seed; the calibrated natural-language judge
(Cohen's kappa >= 0.8 against human raters) is the trusted upgrade and stays gated.

The RARE BONUS layer, reconciling against the realized outcome (Regime E), is GATED. It needs a
corpus of reconciled outcome pairs (controlled, powered, lag-honest) that does not exist yet
(F.1). It is exposed as score_realized_outcome(), which returns status="blocked" with the reason,
never a number, so a missing outcome is reported honestly rather than guessed.

Honest registry note: the outcome-lookup family is registered but EMPTY until F.1 lands the
pairs. This grader registers ONLY its judge-flag part. score_realized_outcome() returns a result
tagged to the outcome-lookup regime, but it registers nothing, so the family table keeps showing
outcome-lookup as a registered-but-empty slot, not as a working grader.
"""
from aievals.graders.base import Grader, GraderResult, register

# The six elements of a quality decision (Spetzler, Decision Quality), scored on the weakest
# link: the decision is only as strong as its weakest element. "reasoning" is the element that
# asks whether the chain from number to action actually follows; "information" asks whether the
# call rests on the validated analysis below it (Tiers 1 to 8), not on assertion.
DECISION_ELEMENTS = ("frame", "alternatives", "information", "values", "reasoning", "commitment")


def evaluate_decision_quality(output):
    """Apply the six-element rubric on the weakest-link rule. `output` carries the recommendation
    and a per-element declaration in output["rubric"] (element -> bool). A missing element reads
    as not-met, never as a free pass. The optional output["rests_on_validated_analysis"] is the
    G37 guard: if the analysis below failed its checks, the "information" element is knocked down
    no matter how fluent the prose. Returns None when there is no recommendation to judge, else a
    dict with the soundness verdict and the failing elements (the weakest links)."""
    if not isinstance(output, dict) or not output.get("recommendation"):
        return None
    rubric = output.get("rubric") or {}
    elements = {e: bool(rubric.get(e, False)) for e in DECISION_ELEMENTS}
    rests = output.get("rests_on_validated_analysis")
    if rests is not None:
        # A recommendation resting on a broken or unvalidated number cannot have sound
        # information, however well it reads. Fold the guard into the information element.
        elements["information"] = elements["information"] and bool(rests)
    failing = [e for e in DECISION_ELEMENTS if not elements[e]]
    return {"sound": not failing, "failing": failing, "elements": elements}


@register
class DecisionGrader(Grader):
    name = "A7-decision"
    family = "judge"            # leans on the expert decision-quality rubric
    truth_basis = "expert"
    surface = "recommendation"
    cost_tier = "operational"   # the decision justifiability flag, added at operational intensity

    def grade(self, output, *, intensity="decision-grade", run_type="single-number", **ctx):
        """The no-outcome process check. Returns a FLAG (would a good analyst make this call on
        this evidence), never a claim that the decision was right and never an outcome number."""
        verdict = evaluate_decision_quality(output)
        if verdict is None:
            return self.result(kind="flag", status="not-applicable", value=None,
                               detail="no recommendation in the output to assess")
        sound = verdict["sound"]
        if sound:
            detail = ("decision quality (process) sound on all six elements. This is process "
                      "quality, not outcome quality: a sound process can still get a bad outcome, "
                      "so this never claims the decision was right.")
        else:
            detail = ("weakest link fails: " + ", ".join(verdict["failing"]) + ". "
                      "A recommendation that does not follow from the analysis (reasoning), or "
                      "rests on a number that failed its checks (information), is not a sound call "
                      "however fluent. Process quality, not outcome quality.")
        return self.result(
            kind="flag",
            status="pass" if sound else "flag",
            value=sound,
            detail=detail,
        )

    def score_realized_outcome(self, recommendation=None, outcome_pair=None, **ctx):
        """The rare bonus layer (Regime E): reconcile the recommendation against what actually
        happened. GATED. It is admissible only from a corpus of reconciled outcome pairs that are
        controlled, powered, and lag-honest, which does not exist yet (F.1). Returns a blocked
        result tagged to the outcome-lookup regime, never a number, so resulting is structurally
        impossible here. This method registers nothing: the outcome-lookup family stays empty."""
        return GraderResult(
            grader=self.name,
            family="outcome-lookup",
            surface="recommendation",
            truth_basis="outcome",
            kind="score",
            status="blocked",
            value=None,
            blocked_on="F.1 reconciled outcome pairs",
            detail=("realized-outcome reconciliation needs >=30 pairs that each clear the five "
                    "admissibility gates (controlled, powered, lag-honest, selection-audited, "
                    "time-decay-flagged). That corpus does not exist yet, so no score is "
                    "computed. Cookie Cats is a worked example of the regime, not a calibrated "
                    "score, and a single outcome never overrides a failed process check."),
        )
