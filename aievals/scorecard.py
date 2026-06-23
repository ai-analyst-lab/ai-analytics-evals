"""C1 The scorecard: roll many graders into one card per analysis, without ever flattening them
into a single cross-regime number.

The card runs the graders the intensity selects, routes by run type, and presents the results
grouped honestly: present versus correct, by truth basis, with a coverage axis. It never adds a
self-consistency flag to a known-answer score, because they are different kinds of truth. The
overall verdict is decided by correctness, not by presence: a garbage number with a perfect
receipt does not score green (the anti-gaming tripwire), and a correct number computed for the
wrong question does not score green either (propagation gating).

Two separations the card states out loud:
  producer is not grader   the thing that produced the answer never grades it; the adapter seam
                           guarantees this, and the card records it.
  present versus correct    a footer being well-formed (presence) is not the number being right
                            (correctness); the card keeps them in separate columns.
"""
from dataclasses import dataclass, field

from aievals.graders.base import select_graders

# Which families speak to correctness (a wrong one fails the card) versus presence or stability
# (surfaced, but never the thing that makes a card green on their own).
CORRECTNESS_FAMILIES = ("computable", "execution")
PRESENCE_FAMILIES = ("inspection",)


@dataclass
class Scorecard:
    question: str
    intensity: str
    run_type: str
    results: list = field(default_factory=list)   # list[GraderResult]
    producer_is_grader: bool = False              # always False via the adapter seam; recorded
    propagation_ok: bool = True                   # False when the question/interpretation is wrong

    def by_truth_basis(self):
        out = {}
        for r in self.results:
            out.setdefault(r.truth_basis, []).append(r)
        return out

    def present_vs_correct(self):
        """Separate presence checks (the receipt is well-formed) from correctness checks (the
        number is right). Kept in different columns so a good receipt never stands in for a right
        answer."""
        present = [r for r in self.results if r.family in PRESENCE_FAMILIES]
        correct = [r for r in self.results if r.family in CORRECTNESS_FAMILIES]
        return {"present": present, "correct": correct}

    def coverage(self):
        """How many surfaces were actually checked (not not-applicable or blocked), of how many
        graders ran. Coverage is its own axis; a card that checked little says so."""
        checked = [r for r in self.results if r.status not in ("not-applicable", "blocked")]
        return {"checked": len(checked), "ran": len(self.results),
                "blocked": len([r for r in self.results if r.status == "blocked"]),
                "not_applicable": len([r for r in self.results if r.status == "not-applicable"])}

    def verdict(self):
        """The overall, non-numeric verdict. Correctness dominates:
          fail  any correctness check failed, or propagation is broken (right number, wrong
                question), regardless of how clean the receipt is. The anti-gaming tripwire.
          flag  no correctness failure, but a check (stability, methodology, decision, judge)
                raised a flag worth a human look.
          pass  the correctness checks that ran passed, propagation holds, and nothing flagged.
          incomplete  no correctness or flag check actually ran (only not-applicable or blocked).
        """
        if not self.propagation_ok:
            return "fail"
        correct = self.present_vs_correct()["correct"]
        if any(r.status == "fail" for r in correct):
            return "fail"
        flagged = [r for r in self.results if r.status == "flag"]
        decided = [r for r in self.results if r.status in ("pass", "fail", "flag")]
        if flagged:
            return "flag"
        if not decided:
            return "incomplete"
        return "pass"

    def as_dict(self):
        return {
            "question": self.question, "intensity": self.intensity, "run_type": self.run_type,
            "verdict": self.verdict(), "coverage": self.coverage(),
            "producer_is_grader": self.producer_is_grader,
            "propagation_ok": self.propagation_ok,
            "results": [r.as_dict() for r in self.results],
        }


def score_analysis(question, output, graders, *, intensity="decision-grade",
                   run_type="single-number", propagation_ok=True, **ctx):
    """Run the graders the intensity selects over one analysis output and return a Scorecard.

    `graders` is a list of grader classes or instances (typically the full registry). The
    intensity selects which run; each grader reads what it needs from `output` and `ctx` and
    returns not-applicable or blocked when its inputs are absent, so the card stays honest about
    what it could and could not check. No result is summed across regimes.
    """
    selected = select_graders(graders, intensity)
    results = []
    for g in selected:
        inst = g() if isinstance(g, type) else g
        results.append(inst.grade(output, intensity=intensity, run_type=run_type, **ctx))
    return Scorecard(question=question, intensity=intensity, run_type=run_type,
                     results=results, propagation_ok=propagation_ok)
