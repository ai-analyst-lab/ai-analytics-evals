"""A1 Reliability, wrapped as a grader (family: self-consistency).

This is the proven check (the deterministic stats), exposed through the grader interface so the
scorecard can roll it in like any other check. It asks the same question N times under one setup
and reads the spread: if the runs converge it is STABLE, if they scatter it is DRIFT.

It is the reference grader for the rest of Track A: a thin shape over a clear computation,
declaring its family, truth basis, surface, and cost tier, returning a GraderResult.

The boundary is load-bearing and stated in the result: convergence is STABILITY, not
correctness. A wrong query can be perfectly stable. So this grader returns a FLAG (stable or
not), never a correctness score. It needs no answer key, which is why it is the cheapest read
and runs at every intensity.
"""
from aievals.graders.base import Grader, register
from aievals.stats.reliability import compute


@register
class ReliabilityGrader(Grader):
    name = "A1-reliability"
    family = "self-consistency"
    truth_basis = "self-consistency"
    surface = "number"
    cost_tier = "exploratory"   # the cheapest read; needs no answer key

    def grade(self, output, *, intensity="decision-grade", run_type="single-number", **ctx):
        """`output` carries the N runs under one setup, as output["runs"] (the block shape the
        stats consume). Returns a stability flag, never a correctness score."""
        runs = output.get("runs") if isinstance(output, dict) else output
        if not runs:
            return self.result(kind="flag", status="not-applicable", value=None,
                               detail="no runs to assess reliability over")
        s = compute(runs)
        verdict = s.get("verdict")
        if verdict == "UNKNOWN":
            return self.result(kind="flag", status="not-applicable", value=None,
                               detail="no parseable numbers in the runs; reliability not assessable")
        stable = verdict == "STABLE"
        return self.result(
            kind="flag",
            status="pass" if stable else "flag",
            value=stable,
            detail=(f"{verdict}: {s.get('n_distinct')} distinct reading(s), "
                    f"agreement {s.get('agreement_rate')}, cited a definition "
                    f"{s.get('used_dictionary')}/{s.get('n')} runs. "
                    "Convergence is stability, not correctness."),
        )
