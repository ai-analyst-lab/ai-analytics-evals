"""A10 Data-fitness (family: judge, frontier).

P-pipeline Piece 1 is the question, and whether the data can even answer it. Its detect side has
two checks: intent clarity (A5) and data fitness. Data fitness asks whether the warehouse actually
holds what the question needs (coverage, grain, freshness, and known gaps) before any SQL runs.
"Why is conversion down" can be answered fluently against a table that does not hold the checkout
funnel at session grain, and the number will look clean while meaning nothing. That is the cheapest
place to be wrong, because every later check inherits the error.

Data-fitness was the one Piece-1 detect check with no Track A grader id, so it is named here for the
same reason A6, A7, and A9 are named-but-flagged: to keep the pipeline's detect side from being
orphaned and to track the frontier item honestly.

The boundary is load-bearing. The "is the data fit" SCORE (grade coverage, grain, freshness, and
known gaps into one fitness reading) is FRONTIER and not built: see fitness_score below, which
returns a blocked marker rather than guessing. The buildable seed is the FLAG: did the analyst state
a data-fitness check at all, and if stated, did it conclude the data cannot answer the question. A
missing check is itself a finding, so the absence of any stated check raises the flag.

The grader reads output["data_fitness"], which may be absent (no check stated) or a dict
{fit: bool, reason}. It returns kind="flag", never a correctness score: data fitness is a precondition
on the question, not a verdict on the answer, and must never be summed into a correctness number.
"""
from aievals.graders.base import Grader, register


def fitness_score(output, **ctx):
    """The graded data-fitness SCORE (coverage, grain, freshness, and known gaps rolled into one
    fitness reading). FRONTIER and BLOCKED: there is no calibrated rubric for turning those four
    dimensions into a trusted number, so this returns a blocked marker instead of a guess. The
    buildable seed is the FLAG below, not this score."""
    return {
        "status": "blocked",
        "blocked_on": "data-fitness scoring is frontier; no calibrated coverage/grain/freshness rubric",
        "value": None,
    }


@register
class DataFitnessGrader(Grader):
    name = "A10-data-fitness"
    family = "judge"
    truth_basis = "expert"
    surface = "data"
    cost_tier = "audit-grade"   # the data-fitness check runs at audit-grade (Piece 1 robust lane)

    def grade(self, output, *, intensity="decision-grade", run_type="single-number", **ctx):
        """`output` may carry output["data_fitness"] = {fit: bool, reason}. The flag fires when no
        fitness check is stated at all, OR when a stated check concludes the data cannot answer the
        question. It passes only when a check is stated and concludes the data is fit. This is a
        precondition flag on the question, never a correctness score on the answer."""
        fitness = output.get("data_fitness") if isinstance(output, dict) else None

        if fitness is None:
            return self.result(
                kind="flag", status="flag", value=True,
                detail=("no data-fitness check stated: whether the data can answer the question "
                        "(coverage, grain, freshness, known gaps) was never asserted. "
                        "A missing check is itself a finding. Fitness scoring is frontier."),
            )

        fit = fitness.get("fit") if isinstance(fitness, dict) else None
        reason = fitness.get("reason", "") if isinstance(fitness, dict) else ""

        if fit:
            return self.result(
                kind="flag", status="pass", value=False,
                detail=(f"data-fitness check stated and concludes the data is fit: {reason}. "
                        "This is a precondition flag, not a correctness score."),
            )

        return self.result(
            kind="flag", status="flag", value=True,
            detail=(f"data-fitness check stated and concludes the data cannot answer the question: "
                    f"{reason}. Stop before any SQL runs. Fitness scoring is frontier."),
        )
