"""Track D: the per-piece pipeline playbook (the second axis).

A real analysis is six pieces, and each piece triggers its own checks on the detect side
(Track A graders) and its own context on the supply side (Track B setups). This encodes that
map, with the per-intensity check counts, so the tool can run a piece-by-piece analysis audit at
the chosen depth, not just isolated checks. The worked example is the spine question: "why is
checkout conversion down this month, and what should we do."

Two patterns from the research hold here: context concentrates at the endpoints (pieces 1 and 6
pull the most setups, the middle pulls less), and the loop runs on every piece (a check surfaces
trouble, a context change fixes it, a re-check confirms). Only piece 3 (the metric definition) is
a fully proven detect-and-fix loop today; the rest are sourced how-to until the build measures
them on NovaMart, and this module says so rather than implying they are all proven.

Source: P-pipeline-playbooks.md, scored in COVERAGE.md.
"""
from dataclasses import dataclass, field

SPINE_QUESTION = "why is checkout conversion down this month, and what should we do"


@dataclass
class Piece:
    n: int
    name: str
    detect: list = field(default_factory=list)   # Track A grader names triggered on the detect side
    supply: list = field(default_factory=list)   # Track B setup keys triggered on the supply side
    per_tier: dict = field(default_factory=dict) # intensity -> count of checks at that tier
    proven: bool = False                         # is this piece a proven detect-and-fix loop today
    note: str = ""


# The six pieces. Grader names match the Track A registry; setup keys match the Track B registry.
# Some detect checks are frontier (A5 intent clarity, A10 data-fitness, A9 confidence as a number)
# and are named here so the pipeline is complete, with the frontier status carried in the note.
PIECES = [
    Piece(1, "question and data-fitness",
          detect=["A5-rubric-judge", "A10-data-fitness", "A1-reliability"],
          supply=["B7-task-scoping", "B1c-company-glossary", "B3-metric-definition"],
          per_tier={"exploratory": 1, "operational": 2, "decision-grade": 3, "audit-grade": 4},
          note="intent clarity (A5) and data-fitness (A10) scoring are frontier; the flags are the buildable seeds"),
    Piece(2, "query",
          detect=["A3-provenance", "A2-known-answer", "A1-reliability"],
          supply=["B4-schema", "B5-query-patterns", "B3-metric-definition"],
          per_tier={"exploratory": 1, "operational": 2, "decision-grade": 3, "audit-grade": 4},
          note="audit adds the A2c regression and ancestor-diff; B5 query patterns are blocked on a seeded fixture"),
    Piece(3, "metric definition",
          detect=["A1-reliability", "A2-known-answer"],
          supply=["B3-metric-definition"],
          per_tier={"exploratory": 1, "operational": 2, "decision-grade": 3, "audit-grade": 3},
          proven=True,
          note="the proven detect-and-fix loop: ask twice, cite the contract, recompute in SQL"),
    Piece(4, "method",
          detect=["A6-methodology", "A4-triangulation"],
          supply=["B5-query-patterns", "B3-metric-definition"],
          per_tier={"exploratory": 1, "operational": 2, "decision-grade": 3, "audit-grade": 4},
          note="audit adds a calibrated judge or human panel (A5), which is gated on calibration"),
    Piece(5, "analysis code and the number",
          detect=["A8-execution", "A2-known-answer", "A1-reliability", "A3-provenance"],
          supply=["B5-query-patterns", "B6-corrections"],
          per_tier={"exploratory": 1, "operational": 2, "decision-grade": 3, "audit-grade": 4},
          note="audit adds a multi-assertion partial-DataFrame suite (A8); B6 corrections blocked on a seeded fixture"),
    Piece(6, "narrative, recommendation, confidence",
          detect=["A5-rubric-judge", "A7-decision", "A4-triangulation", "A3-provenance", "A9-confidence"],
          supply=["B7-task-scoping", "B3-metric-definition"],
          per_tier={"exploratory": 1, "operational": 3, "decision-grade": 4, "audit-grade": 6},
          note="audit adds a calibrated judge and, where it exists, a realized-outcome check (A7, gated)"),
]


def piece(n):
    for p in PIECES:
        if p.n == n:
            return p
    raise KeyError(f"no pipeline piece {n}; pieces are 1..{len(PIECES)}")


def checks_for(n, intensity):
    """The number of checks piece n runs at this intensity, per the playbook's per-tier counts."""
    p = piece(n)
    if intensity not in p.per_tier:
        raise ValueError(f"unknown intensity {intensity!r}")
    return p.per_tier[intensity]


def endpoints_pull_most():
    """The research pattern, made checkable and stated honestly: context concentrates at the
    endpoints. This holds ON AVERAGE, not as a per-piece maximum: the query piece (2) legitimately
    pulls schema, patterns, and the contract, so it ties piece 1 on raw count. Returns True when
    the endpoint pieces (1 and 6) pull more setups on average than the middle pieces (2 to 5).
    Note also that some of piece 6's context (audience profile, provenance templates, confidence
    rules) is real but not yet instantiated as its own B-unit, so the registered count understates
    the endpoint concentration rather than overstating it."""
    counts = {p.n: len(p.supply) for p in PIECES}
    endpoints_avg = (counts[1] + counts[6]) / 2
    middle_avg = sum(counts[n] for n in (2, 3, 4, 5)) / 4
    return endpoints_avg > middle_avg
