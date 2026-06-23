"""A6 Methodology justifiability (family: judge), a FLAG, never a correctness score.

This grader answers a question the rest of Track A does not: was the analytical APPROACH
defensible for the question being asked. It does not ask whether the method was the single
"right" one, because that question is often incoherent. Good analysts pick different defensible
methods for the same question, and those methods target different estimands (ATE vs ATT vs
LATE are different real quantities), so anointing one "correct" is false precision sitting on
top of irreducible human disagreement. That is the locked decision: A6 emits a flag, not a
score.

What the flag DOES check is justifiability, the presence of a rationale, which is objective:
  1. question-type match, the method's analytic family fits the question's type (a causal
     question answered with a bare before-and-after slice is a wrong-type error, the agent's
     most common method failure),
  2. a stated estimand, the target quantity is named, so a reviewer can see which question
     among the defensible variants is being answered,
  3. a named identifying assumption, the method's key assumption is stated (parallel trends
     for DiD, ignorability for matching, and so on).

Missing any of the three is an objective justifiability failure, so the flag fires. All three
present means the choice is justified (a different good analyst might still pick a different
defensible method, but that is a disagreement signal, not a fail).

EXPLICITLY NOT BUILT (frontier): the "is the method RIGHT" correctness score. That needs a
kappa-calibrated judge against an expert panel (V-methodology.md section 4, gated on W4.1), and
section 3 argues a method-correctness score may be philosophically incoherent on contested
questions. We refuse to fake it. The frontier hook (method_correctness_score) returns a blocked
marker so a contested method is never silently scored as correct. Likewise the divergence
classifier (estimand-conflict vs assumption-failure vs wrong-type, section 3a) is design, not
built here.

Source: V-methodology.md (BLADE precursor, the four-part justifiability rubric, GAP G25/G26/G114).
"""
from aievals.graders.base import Grader, register


def _norm(method_type):
    """Normalize a method-type label so 'Difference in Differences', 'difference_in_differences'
    and 'difference-in-differences' all key the same."""
    if not method_type:
        return ""
    return "-".join(str(method_type).strip().lower().replace("_", " ").split())


# The analytic family each named method belongs to. The four families come from the classic
# analytics taxonomy (descriptive / diagnostic / causal / predictive). A before-and-after (a
# pre/post slice) is DESCRIPTIVE, it confounds time, which is why it is the canonical wrong-type
# choice for a causal question.
METHOD_FAMILIES = {
    # descriptive, "what happened"
    "aggregation": "descriptive",
    "segmentation": "descriptive",
    "trend": "descriptive",
    "before-and-after": "descriptive",
    "pre-post": "descriptive",
    "descriptive-comparison": "descriptive",
    # diagnostic / root-cause, "why"
    "funnel-decomposition": "diagnostic",
    "cohort-contribution": "diagnostic",
    "segment-contribution": "diagnostic",
    "root-cause-decomposition": "diagnostic",
    "rca": "diagnostic",
    # causal, "what is the effect of X"
    "did": "causal",
    "difference-in-differences": "causal",
    "regression-with-controls": "causal",
    "regression": "causal",
    "synthetic-control": "causal",
    "matching": "causal",
    "psm": "causal",
    "ab-test": "causal",
    "experiment": "causal",
    # predictive, "what will happen"
    "forecasting": "predictive",
    "time-series": "predictive",
}

# Which analytic families are defensible for each question type (V-methodology section 1a).
DEFENSIBLE = {
    "descriptive": {"descriptive"},
    "diagnostic": {"diagnostic"},
    "causal": {"causal"},
    "predictive": {"predictive"},
}


def method_family(method_type):
    """The analytic family of a named method (descriptive / diagnostic / causal / predictive),
    or None if the method label is unknown to the map."""
    return METHOD_FAMILIES.get(_norm(method_type))


def type_matches(question_type, method_type):
    """True if the method's analytic family is in the defensible set for the question type.
    A None on either side, or an unknown method, is NOT a match (we cannot confirm a fit)."""
    qt = _norm(question_type)
    fam = method_family(method_type)
    if not qt or fam is None or qt not in DEFENSIBLE:
        return False
    return fam in DEFENSIBLE[qt]


def method_correctness_score(method, question_type, **ctx):
    """The "is the chosen method RIGHT" score. FRONTIER and NOT BUILT: it needs a kappa-calibrated
    judge against an expert panel (V-methodology section 4, gated on W4.1), and section 3 argues
    the score may be incoherent because defensible methods target different estimands. Returns a
    blocked marker instead of a guess, so a contested method is never silently scored correct."""
    return {
        "status": "blocked",
        "blocked_on": "W4.1 expert method-choice panel (kappa calibration); section 3 incoherence",
        "score": None,
    }


@register
class MethodologyGrader(Grader):
    name = "A6-methodology"
    family = "judge"
    truth_basis = "expert"
    surface = "method"
    cost_tier = "operational"

    def grade(self, output, *, intensity="decision-grade", run_type="single-number", **ctx):
        """`output` carries output["method"] = {type, estimand, identifying_assumption} and
        output["question_type"]. Returns a justifiability FLAG, never a correctness score:
        status "pass" when the method type fits the question AND the estimand and identifying
        assumption are both named; status "flag" when any of the three is missing or mismatched.
        """
        method = output.get("method") if isinstance(output, dict) else None
        question_type = output.get("question_type") if isinstance(output, dict) else None

        if not method and not question_type:
            return self.result(kind="flag", status="not-applicable", value=None,
                               detail="no method choice or question type to assess")
        if not isinstance(method, dict) or not method:
            return self.result(
                kind="flag", status="flag", value=False,
                detail="method not stated; cannot justify an unstated approach. "
                       "This is a justifiability flag, not a correctness score.")

        m_type = method.get("type")
        estimand = method.get("estimand")
        assumption = method.get("identifying_assumption")

        type_ok = type_matches(question_type, m_type)
        estimand_ok = bool(estimand and str(estimand).strip())
        assumption_ok = bool(assumption and str(assumption).strip())

        failures = []
        if not type_ok:
            fam = method_family(m_type)
            fam_note = fam if fam is not None else "unknown method family"
            failures.append(
                f"wrong-type: a {m_type!r} method ({fam_note}) does not fit a "
                f"{question_type!r} question")
        if not estimand_ok:
            failures.append("estimand not stated")
        if not assumption_ok:
            failures.append("identifying assumption not named")

        justified = type_ok and estimand_ok and assumption_ok
        if justified:
            detail = (f"justifiable: {m_type!r} fits a {question_type!r} question; estimand "
                      f"({estimand}) and identifying assumption ({assumption}) are named. "
                      "Justifiability, not correctness: a different good analyst may pick a "
                      "different defensible method, which is a disagreement signal, not a fail.")
        else:
            detail = ("not justifiable: " + "; ".join(failures) +
                      ". This is a justifiability flag, not a method-correctness score "
                      "(the correctness score is frontier and not built).")

        return self.result(kind="flag", status="pass" if justified else "flag",
                           value=justified, detail=detail)
