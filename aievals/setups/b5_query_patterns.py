"""B5 Query patterns / gold SQL (canonical layer L4): the toggle mechanism, honestly blocked.

A validated query pattern is a curated piece of L4 data-infrastructure context: a gold SQL shape
tied to a recurring spine question, so the agent reuses a query that is known to join and filter
correctly instead of re-deriving one (and drifting) each run. Staging that context on or off is
the same file-reader toggle the other B units use, so the MECHANISM is buildable now and is what
this module gives you.

What does not exist yet is the content to toggle. The ai-analyst-plus query-archaeology curated
dirs (`.knowledge/query-archaeology/curated/{tables,joins,cookbook}/`) are empty (only `.gitkeep`
and an empty `index.yaml`), so there is no validated pattern for the "with" side of the comparison.
A real fixture (a curated gold-SQL pattern tied to a NovaMart spine question, validated against
live NovaMart) is seeded separately by the maintainer. Until then this unit reports status
"blocked" and the builder defaults to staging nothing (patterns_dir=None), which the reader reads
as an empty overlay list. That is the honest "with" side: empty, because no pattern is curated yet.
"""
from aievals.harness.setups import Setup
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup

# The seeded, NovaMart-verified gold-SQL pattern (checkout conversion, with the quirk guard). The
# SQL shape is validated against the NovaMart practice data and computes its answer at eval time
# (no answer is stored in the pattern).
PATTERNS_FIXTURE = FIXTURES / "query_patterns"


def build(patterns_dir=None, **ctx):
    """Return the with-patterns setup: a Setup that points the file reader at a directory of
    validated query-pattern YAML. `patterns_dir` is supplied by the caller (analyst-side, the
    curated query-archaeology dir) or defaults to the bundled NovaMart-verified pattern, so the
    with arm stages a real gold-SQL shape rather than nothing. The no-pattern baseline is
    Setup(name=..., layer=None, spec=None)."""
    spec = str(patterns_dir) if patterns_dir is not None else str(PATTERNS_FIXTURE)
    return Setup(name="with-query-patterns", layer="L4", reader="file", spec=spec)


def baseline():
    """The no-pattern arm: the agent re-derives the query each run, with no validated shape to
    reuse. This is what the with-patterns arm is compared against once a fixture exists."""
    return Setup(name="no-query-patterns", layer=None, reader="file", spec=None)


register_setup(SetupSpec(
    key="B5-query-patterns",
    layer="L4",
    status="partial",
    summary="Stage validated query patterns (gold SQL) on or off; the toggle works and a real "
            "NovaMart-verified pattern is seeded; the live drift-collapse proof needs an agentic run.",
    blocked_on="the end-to-end behavioral proof (the query that needs the pattern succeeds where "
               "the no-pattern run drifts) needs a live agentic run. The pattern fixture itself is "
               "real and NovaMart-verified (checkout conversion with the had_purchase quirk guard), "
               "so the unit is no longer blocked on a fixture, only on the live run.",
    source="C-store.md",
    build=build,
))
