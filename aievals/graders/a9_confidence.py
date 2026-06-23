"""A9 Confidence tier (family: computable, FRONTIER, taught as a concept).

The last mile of the pipeline is where a shaky number becomes a confident sentence. The failure
mode is tone: a result that rests on one run, off a raw source, with no validation, gets narrated
with the same certainty as one that was triangulated, validated, and pulled from a governed table.
A model that is asked "how confident are you" will happily answer, and that self-report is exactly
the thing not to trust. So A9 derives confidence the only honest way: from the provenance of the
work itself (the source tier the number came from, whether it passed validation, and how many runs
back it), never from what the model says about itself.

Per the locked no-number rule this presents NO confidence number. There is no 0.82, no percent, no
score to sum. The output is an ordinal LABEL ("low" / "medium" / "high"), surfaced so a reader can
weight the claim, taught as a concept rather than trusted as a measurement. The derivation is a
weakest-link rule: confidence is bounded by the weakest of its three legs, because a governed,
validated number that rests on a single run is still a single-run number. That is why this returns
a FLAG (a surfaced label) and never a score: a tier label must never be added into a correctness
total, and the tier is not a claim that the answer is correct.

FRONTIER. The deterministic tier MECHANISM is buildable now and is what ships and is tested here.
Confidence as a trusted, calibrated quantity is not built and is not the goal; the model's
self-reported confidence (output["model_confidence"]) is read past and ignored on purpose, and the
test proves changing it does not move the tier.

Source: P-pipeline-playbooks Piece 6 ("a confidence tier derived deterministically rather than from
the model's self-report"), BUILD_STATUS W5.2.
"""
from aievals.graders.base import Grader, register

# The three ordinal rungs the tier can land on, weakest first. These are labels, not numbers: their
# only order is positional, and nothing downstream may treat the index as a confidence value.
TIERS = ("low", "medium", "high")

# Each leg maps an input to one of the three rungs. An input we do not recognize falls to the
# weakest rung on purpose: an unknown provenance is not evidence of a strong one.

# How governed the data the number came from is. Common synonyms for each rung, lowercased.
SOURCE_TIER_RANK = {
    "certified": 2, "governed": 2, "gold": 2, "trusted": 2,
    "modeled": 1, "derived": 1, "silver": 1, "curated": 1,
    "raw": 0, "adhoc": 0, "ad-hoc": 0, "bronze": 0, "unknown": 0,
}

# Whether the number passed a validation check (a known-answer gold, a contract, a calibrated judge).
VALIDATION_RANK = {
    "validated": 2, "passed": 2, "gold-checked": 2,
    "partial": 1, "self-consistent": 1, "stable": 1,
    "unvalidated": 0, "failed": 0, "none": 0, "blocked": 0, "drift": 0,
}


def _source_rung(source_tier):
    """The source leg's rung. Unrecognized or missing source falls to the weakest rung."""
    if source_tier is None:
        return 0
    return SOURCE_TIER_RANK.get(str(source_tier).strip().lower(), 0)


def _validation_rung(validation_status):
    """The validation leg's rung. Unrecognized or missing status falls to the weakest rung."""
    if validation_status is None:
        return 0
    return VALIDATION_RANK.get(str(validation_status).strip().lower(), 0)


def _run_count_rung(run_count):
    """The run-count leg's rung. One run (or fewer, or unparseable) is the weakest rung, because a
    single run cannot speak to stability; two is the middle rung; three or more is the top rung."""
    try:
        n = int(run_count)
    except (TypeError, ValueError):
        return 0
    if n >= 3:
        return 2
    if n == 2:
        return 1
    return 0


def deterministic_tier(source_tier, validation_status, run_count):
    """Derive the confidence tier from provenance alone, by the weakest-link rule.

    The tier is the lowest rung of the three legs: a chain is only as strong as its weakest link,
    so a number is only as confident as its weakest leg of provenance. Returns a label from TIERS,
    never a number, and never reads any model self-report (it is not a parameter here).
    """
    rung = min(
        _source_rung(source_tier),
        _validation_rung(validation_status),
        _run_count_rung(run_count),
    )
    return TIERS[rung]


@register
class ConfidenceTierGrader(Grader):
    name = "A9-confidence"
    family = "computable"
    truth_basis = "computable"
    surface = "confidence"
    cost_tier = "decision-grade"

    def grade(self, output, *, intensity="decision-grade", run_type="single-number", **ctx):
        """`output` carries the provenance legs the tier is derived from:
          output["source_tier"]        how governed the data the number came from is
          output["validation_status"]  whether the number passed a validation check
          output["run_count"]          how many runs back the number
        and output["model_confidence"], the model's self-report, which is read past and IGNORED.

        Returns a FLAG whose value is the ordinal tier LABEL (a string), never a number and never a
        correctness score. If no provenance is supplied at all, reports not-applicable honestly.
        """
        if not isinstance(output, dict):
            return self.result(kind="flag", status="not-applicable", value=None,
                               detail="no provenance supplied; a confidence tier needs source, "
                                      "validation status, and run count")

        legs = ("source_tier", "validation_status", "run_count")
        if not any(k in output for k in legs):
            return self.result(kind="flag", status="not-applicable", value=None,
                               detail="no provenance legs present (source_tier / validation_status "
                                      "/ run_count); tier not derivable")

        source_tier = output.get("source_tier")
        validation_status = output.get("validation_status")
        run_count = output.get("run_count")
        tier = deterministic_tier(source_tier, validation_status, run_count)

        # The model's self-report is deliberately read and discarded: we note that it was present so
        # the detail is honest, but it does not enter the derivation.
        self_report = output.get("model_confidence")
        ignored = (f"; model self-report ({self_report!r}) ignored by design"
                   if self_report is not None else "")

        return self.result(
            kind="flag",
            status="flag",
            value=tier,
            detail=(f"tier '{tier}' by weakest-link of source={source_tier!r}, "
                    f"validation={validation_status!r}, run_count={run_count!r}{ignored}. "
                    "Derived from provenance, never from the model self-report; an ordinal label, "
                    "not a confidence number (frontier, taught as a concept)."),
        )
