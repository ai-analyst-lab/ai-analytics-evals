"""B6 Corrections and learnings (canonical layer L5): stage the corrections store on or off.

L5 is the accumulated-memory layer, the mistake log and the learnings the agent carries forward
so a known error does not recur. A correction is procedural memory: it records how to query the
data correctly (the wrong move, the fix, the right SQL shape), never a result number. The point
of the unit is to make that store a toggleable, comparable setup like every other layer, so a
comparison run can ask the intended question: with the relevant correction staged, does the known
mistake stop recurring, and without it, does it come back?

The toggle MECHANISM is buildable now and is what this module provides: the with-corrections arm
points a source-reader at a directory of correction YAML, the off arm stages nothing, and the two
arms differ only by whether the store is loaded. It is the same pure-staging mechanism the B3
retention contract proved, applied to the L5 layer.

The unit as a whole is BLOCKED, and the status carried in code says so honestly. The canonical
corrections store at ~/projects/ai-analyst-plus/.knowledge/corrections/ is empty (only a
log.template.yaml), so there is no real correction tied to a reproducible NovaMart mistake to
toggle against: the "with" side of the comparison has nothing to load. That fixture is seeded
separately against live NovaMart (a correction whose absence makes a known mistake recur). Until
it exists, build(corrections_dir=None) stages an empty store, which is the honest default: there
is no teaching fixture baked in, because the whole point is blocked on a real one. A caller (or
the seeding step) supplies corrections_dir to point the reader at a real store, so the eval tool
holds no analyst-private path. The correction store carries no result number by design (a fix is
a query shape and a rule, not an answer the agent should recall), matching the meaning-only
discipline of every other Track B layer.

Source: C-memory.md (the typed proposed -> verified store, the "retention is 9%" poison-pill
failure mode), C-store.md.
"""
from aievals.harness.setups import Setup
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup

# The seeded, NovaMart-verified correction store (the had_purchase Q4-2024 mistake). A real fixture,
# not a placeholder: the mistake it corrects is reproducible on the NovaMart practice data.
CORRECTIONS_FIXTURE = FIXTURES / "corrections"


def build(corrections_dir=None, **ctx):
    """Return the with-corrections setup (the on arm). `corrections_dir` is the directory holding
    the correction YAML; analyst-side when testing a real analyst, or the bundled seeded fixture by
    default. The default is the NovaMart-verified correction store, so the with arm stages a real
    correction rather than an empty placeholder. The off arm is baseline()."""
    spec = str(corrections_dir) if corrections_dir is not None else str(CORRECTIONS_FIXTURE)
    return Setup(name="with-corrections", layer="L5", reader="file", spec=spec)


def baseline():
    """The no-corrections arm: the bare baseline the with-corrections arm is compared against. It
    stages no L5 content, so the agent carries no accumulated memory and a known mistake is free to
    recur."""
    return Setup(name="no-corrections", layer=None, reader="file", spec=None)


def compose_corrections(overlays):
    """Merge correction overlays into one list (the learnings the agent carries forward). This
    parallels compose_metrics for the L5 layer: each overlay carries its own `corrections` list.
    Off-arm overlays are empty, so this returns an empty list and the toggle is visible as the
    difference between the two arms."""
    corrections = []
    for ov in overlays:
        corrections.extend((ov or {}).get("corrections", []))
    return corrections


register_setup(SetupSpec(
    key="B6-corrections",
    layer="L5",
    status="partial",
    summary="Stage the corrections store on or off; the toggle works and a real NovaMart-verified "
            "correction is seeded; the live does-not-recur proof needs an agentic run.",
    blocked_on=(
        "the end-to-end behavioral proof (with the correction staged the known mistake stops "
        "recurring, without it it recurs) needs a live agentic run, which is the agent run step. "
        "The correction fixture itself is real and NovaMart-verified (the had_purchase Q4-2024 "
        "mistake), so the unit is no longer blocked on a fixture, only on the live run."
    ),
    source="C-memory.md, C-store.md",
    build=build,
))
