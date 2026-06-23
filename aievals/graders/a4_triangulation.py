"""A4 Triangulation (family: self-consistency).

Ask the same business question through several independent arms and check whether they agree on
the DECISION DIRECTION (up, down, or flat), not on the number. Across methods the numbers will
differ and should: a cohort comparison, a difference-in-differences, and a controlled regression
answer "did the pricing change hurt retention?" with three different figures but, if the analysis
is sound, the same sign and the same implied action. So this grader reduces each arm to a
direction token and asks one thing: do the arms point the same way?

This is the cross-arm case of self-consistency (A1 is the within-method, repeated-run case). Like
A1 it returns a FLAG, never a correctness score, because the boundary is load-bearing and stated
in the result: convergence is evidence of RELIABILITY, not a proof of CORRECTNESS. Correlated
arms (a shared data path, a shared assumption about the grain, the same wrong metric definition
fed to every arm) can agree and all be wrong, which looks exactly like real convergence. The
result carries an independence caveat for that reason, and notes that effective-vote (n_eff)
measurement is not yet wired.

Method triangulation on computable questions is buildable now: the direction-agreement math needs
no second model. MULTI-MODEL triangulation (fanning the same question to a different model family)
depends on Layer 0.5, a second model being wired. When an arm declares itself model-based and no
distinct second model is present, the result says so: that arm is partial-until-second-model.
"""
from aievals.graders.base import Grader, register

# Direction synonyms folded onto three canonical tokens. A metric is defined by meaning, so an arm
# may report its direction in whatever words it used; we normalize, never hardcode an answer.
_DIRECTION_SYNONYMS = {
    "up": "up", "increase": "up", "increased": "up", "higher": "up", "positive": "up",
    "rise": "up", "rose": "up", "+": "up",
    "down": "down", "decrease": "down", "decreased": "down", "lower": "down",
    "negative": "down", "fall": "down", "fell": "down", "drop": "down", "-": "down",
    "flat": "flat", "no-effect": "flat", "no_effect": "flat", "none": "flat",
    "no-change": "flat", "no_change": "flat", "neutral": "flat", "0": "flat", "zero": "flat",
}


def normalize_direction(token):
    """Fold a free-form direction word onto up / down / flat, or None if it is not parseable.
    Comparing direction tokens (not raw figures) is the whole point of method triangulation."""
    if token is None:
        return None
    key = str(token).strip().lower()
    return _DIRECTION_SYNONYMS.get(key)


def _arm_modality(arm):
    """An arm is method-based by default (buildable now). It can declare modality='model' to mark
    itself as a model-triangulation arm, which carries the Layer 0.5 dependency."""
    return (arm.get("modality") or "method").strip().lower() if isinstance(arm, dict) else "method"


@register
class TriangulationGrader(Grader):
    name = "A4-triangulation"
    family = "self-consistency"
    truth_basis = "self-consistency"
    surface = "decision"
    cost_tier = "decision-grade"   # the full set triangulates; not the cheapest read

    def grade(self, output, *, intensity="decision-grade", run_type="single-number", **ctx):
        """`output` carries the arms as output['arms'] = list of {name, direction}, optionally
        {name, direction, modality, model}. Returns a direction-agreement flag, never a score."""
        arms = output.get("arms") if isinstance(output, dict) else output
        if not arms:
            return self.result(
                kind="flag", status="not-applicable", value=None,
                detail="no arms to triangulate; supply output['arms'] as [{name, direction}, ...]")

        parsed, unparseable = [], []
        for arm in arms:
            name = (arm.get("name") if isinstance(arm, dict) else None) or "?"
            d = normalize_direction(arm.get("direction") if isinstance(arm, dict) else arm)
            (parsed if d is not None else unparseable).append((name, d if d is not None else "?"))

        if len(parsed) < 2:
            return self.result(
                kind="flag", status="not-applicable", value=None,
                detail=("triangulation needs at least 2 arms with a parseable direction; "
                        f"got {len(parsed)} parseable, unparseable arms: "
                        f"{[n for n, _ in unparseable]}"))

        directions = {d for _, d in parsed}
        agree = len(directions) == 1

        # Multi-model arms carry the Layer 0.5 dependency: real model triangulation needs a second
        # distinct model. With fewer than two distinct models, those arms are partial-until-second-model.
        model_arms = [a for a in arms if isinstance(a, dict) and _arm_modality(a) == "model"]
        distinct_models = {(a.get("model") or a.get("name")) for a in model_arms}
        multimodel_note = ""
        if model_arms and len(distinct_models) < 2:
            multimodel_note = (" Multi-model arm is partial-until-second-model: real model "
                               "triangulation needs a distinct second model (Layer 0.5), not yet wired.")

        # The independence caveat is load-bearing: agreement only counts if the arms are independent.
        independence_note = (" Agreement counts only if the arms are independent; correlated arms "
                             "(shared data path, shared assumption, same metric definition) manufacture "
                             "convergence. Effective-vote (n_eff) measurement is not yet wired.")

        if agree:
            verdict = next(iter(directions))
            detail = (f"{len(parsed)} arms agree on direction '{verdict}' "
                      f"({', '.join(n for n, _ in parsed)})." + independence_note + multimodel_note +
                      " Convergence is reliability evidence, not correctness.")
            return self.result(kind="flag", status="pass", value=True, detail=detail)

        split = ", ".join(f"{n}={d}" for n, d in parsed)
        detail = (f"arms diverge across {len(directions)} directions: {split}. Route the diverging "
                  "arm to its trace before trusting either." + independence_note + multimodel_note +
                  " Convergence is reliability evidence, not correctness.")
        return self.result(kind="flag", status="flag", value=False, detail=detail)
