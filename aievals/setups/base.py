"""The setup registry: every context-stack setup, with its honest status carried in code.

A Track B unit becomes a SetupSpec: which canonical layer it touches, its honest status
(buildable-now, blocked, partial, frontier, or described-only) and what it is blocked on, and a
builder that returns the Setup object(s) the comparison run toggles. Self-registering, so units
do not edit a central list and the status lives next to the code, not only in a doc.

A builder receives a context dict (for example a knowledge_root path the caller owns) and returns
a Setup or a list of Setups (a multi-arm experiment like the three format variants). The eval
tool holds no analyst-private path; the builder is handed the root it should read from.
"""
from dataclasses import dataclass, field

# The honest status of a setup, carried into code and reported as-is.
STATUSES = ("buildable-now", "blocked", "partial", "frontier", "described-only")


@dataclass
class SetupSpec:
    key: str
    layer: str               # the canonical layer (L0-L6), or None for a cross-cutting axis
    status: str
    summary: str = ""
    blocked_on: str = None
    source: str = ""         # the research/decision doc this traces to
    build: object = None     # build(**ctx) -> Setup | list[Setup]; None if not yet runnable

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"unknown status {self.status!r}; must be one of {STATUSES}")


_REGISTRY = {}


def register_setup(spec):
    """Register a SetupSpec by key. Decorator-friendly: returns the spec."""
    if not isinstance(spec, SetupSpec):
        raise TypeError("register_setup expects a SetupSpec")
    _REGISTRY[spec.key] = spec
    return spec


def registry():
    return dict(_REGISTRY)


def by_status(status):
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    return [s for s in _REGISTRY.values() if s.status == status]


def status_table():
    """Every registered setup, grouped by status. The honest map of what is runnable now versus
    blocked, partial, frontier, or described-only."""
    return {st: [s.key for s in _REGISTRY.values() if s.status == st] for st in STATUSES}
