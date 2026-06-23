"""The grader interface: one uniform shape every validation check implements.

A grader takes an analysis output and returns a per-surface result. Graders are
interchangeable because they all return the same shape, and the scorecard can roll many of
them into one card without ever adding scores across regimes: a stability flag and a
known-answer score are different kinds of truth and must never be summed into one number.

Each grader declares its FAMILY, so the orchestrator can route a run to the right family, and
its COST_TIER, so the selector can choose how many checks to run for the stakes. The six
families are fixed here. A family may be registered but empty: outcome-lookup ships with zero
members until reconciled outcome pairs exist, and that is reported honestly, not hidden.
"""
from dataclasses import dataclass

# The six grader families. Reconciled with BUILD_STATUS W3b.1's five plus self-consistency
# (the reliability and triangulation graders route here), so nothing routes to a name that
# does not exist. A family may be registered but empty.
FAMILIES = (
    "computable",        # a number checked against a gold computed in SQL at eval time
    "execution",         # code run against a known-answer case, tests as truth, no model in the loop
    "judge",             # an LLM judge against a written rubric (not trusted until calibrated)
    "inspection",        # presence and well-formedness of what the answer carries (the receipt)
    "outcome-lookup",    # the realized outcome, looked up later (gated on reconciled pairs)
    "self-consistency",  # the spread across repeated or triangulated runs (stability, not truth)
)

# How a grader's value reads. A score lives inside ONE regime; a flag is a yes/no the scorecard
# surfaces but never rolls into a correctness number.
KINDS = ("score", "flag")

# The truth a grader leans on. Distinct from family: the judge family leans on expert labels,
# the inspection family on presence.
TRUTH_BASES = ("computable", "execution", "expert", "presence", "self-consistency", "outcome")

# The four intensity rungs, cheapest first. A grader is selected when its cost tier is at or
# below the requested intensity (heavy graders only at audit-grade).
RUNGS = ("exploratory", "operational", "decision-grade", "audit-grade")

# The run's shape, which routes it to the families that can grade it.
RUN_TYPES = ("single-number", "set", "table", "free-text-with-claims")

# Statuses a grader can report. "blocked" carries a reason; "not-applicable" means this grader
# does not apply to this run type, which is honest, not a pass.
STATUSES = ("pass", "fail", "flag", "blocked", "not-applicable")


@dataclass
class GraderResult:
    """One grader's verdict on one surface of one analysis. Never additive across regimes."""
    grader: str
    family: str
    surface: str            # the analysis surface judged: number, sql, method, narrative, ...
    truth_basis: str
    kind: str               # "score" or "flag"
    status: str             # pass / fail / flag / blocked / not-applicable
    value: object = None    # a score in [0,1] when kind=score; True/False when kind=flag; None if blocked
    detail: str = ""
    blocked_on: str = None

    def __post_init__(self):
        if self.family not in FAMILIES:
            raise ValueError(f"unknown family {self.family!r}; must be one of {FAMILIES}")
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind {self.kind!r}; must be one of {KINDS}")
        if self.truth_basis not in TRUTH_BASES:
            raise ValueError(f"unknown truth_basis {self.truth_basis!r}; must be one of {TRUTH_BASES}")
        if self.status not in STATUSES:
            raise ValueError(f"unknown status {self.status!r}; must be one of {STATUSES}")

    def as_dict(self):
        return {
            "grader": self.grader, "family": self.family, "surface": self.surface,
            "truth_basis": self.truth_basis, "kind": self.kind, "status": self.status,
            "value": self.value, "detail": self.detail, "blocked_on": self.blocked_on,
        }


class Grader:
    """Base class for a validation check. Subclass it, set the class attributes, implement grade().

    Class attributes a subclass MUST set:
      name        a stable id, for example "A2-known-answer"
      family      one of FAMILIES
      truth_basis one of TRUTH_BASES
      surface     the analysis surface it judges (number, sql, method, narrative, ...)
      cost_tier   the cheapest intensity at which this grader runs (one of RUNGS)
      heavy       True if it is audit-grade-only heavy machinery (default False)

    grade() receives the analysis output plus the run `intensity` and `run_type`, and returns a
    GraderResult. Use self.result(...) to build one tagged with this grader's family and surface.
    """
    name = "base"
    family = None
    truth_basis = None
    surface = None
    cost_tier = "decision-grade"
    heavy = False

    def grade(self, output, *, intensity="decision-grade", run_type="single-number", **ctx):
        raise NotImplementedError

    def result(self, *, kind, status, value=None, detail="", blocked_on=None):
        return GraderResult(
            grader=self.name, family=self.family, surface=self.surface,
            truth_basis=self.truth_basis, kind=kind, status=status,
            value=value, detail=detail, blocked_on=blocked_on,
        )


_REGISTRY = {}


def register(grader_cls):
    """Class decorator: register a grader by name. Self-declaring, so grader modules do not
    edit a central list and parallel additions never collide. Validates the declared family
    and cost tier at registration."""
    if grader_cls.family not in FAMILIES:
        raise ValueError(f"{grader_cls.name}: unknown family {grader_cls.family!r}")
    if grader_cls.cost_tier not in RUNGS:
        raise ValueError(f"{grader_cls.name}: unknown cost_tier {grader_cls.cost_tier!r}")
    if grader_cls.truth_basis not in TRUTH_BASES:
        raise ValueError(f"{grader_cls.name}: unknown truth_basis {grader_cls.truth_basis!r}")
    _REGISTRY[grader_cls.name] = grader_cls
    return grader_cls


def registry():
    """All registered graders, by name."""
    return dict(_REGISTRY)


def by_family(family):
    """The registered graders for one family (possibly an empty list)."""
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}")
    return [g for g in _REGISTRY.values() if g.family == family]


def family_table():
    """The honest family map: every family, and the graders registered to it. A family with no
    members (outcome-lookup, until reconciled pairs exist) shows as an empty list, not as absent."""
    return {fam: [g.name for g in _REGISTRY.values() if g.family == fam] for fam in FAMILIES}


def select_graders(graders, intensity):
    """Which graders run at this intensity. Monotone in the rung order:
      exploratory    the one cheapest read
      operational    one or two checks
      decision-grade the full set (everything that is not audit-only heavy machinery)
      audit-grade    the full set plus the heavy machinery

    `graders` is a list of grader classes or instances. Returns the selected subset, in order.
    """
    if intensity not in RUNGS:
        raise ValueError(f"unknown intensity {intensity!r}; must be one of {RUNGS}")
    want = RUNGS.index(intensity)
    chosen = []
    for g in graders:
        if g.heavy and intensity != "audit-grade":
            continue
        if RUNGS.index(g.cost_tier) <= want:
            chosen.append(g)
    return chosen
