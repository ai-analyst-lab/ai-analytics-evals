"""B4 Schema and quirks (canonical layer L4): stage the data-infrastructure context on or off.

The L4 layer is what the agent links a question against: the tables, their grain and keys, the
joins between them, and the quirks (the gotchas that silently corrupt a query when the agent
does not know them, like cancelled orders that keep their row or timestamps stored in UTC).
Without this layer an agent guesses the schema from column names and folklore, which is where
schema-linking errors and answer drift come from. This unit makes the layer a toggleable setup
so a comparison run can ask the intended question: does staging the schema-and-quirks overlay
reduce drift or schema-linking errors versus running with no schema context at all?

The unit is buildable now because it is pure staging, the same proven mechanism as the B3
retention contract: the with-schema arm points a source-reader at a schema overlay and composes
it, the off arm stages nothing. It carries no analyst-private path (the caller supplies the
directory the overlay lives in, or omits it to use our canonical teaching fixture) and no result
number (the overlay is structure and warnings, the agent still computes every figure from the
data). The honest status lives in code: status="buildable-now", blocked_on=None.
"""
from aievals.harness.setups import Setup
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup

# Our canonical teaching fixture for the schema layer, parallel to the retention contract. Not an
# analyst path: the caller passes schema_dir to point at a real analyst's L4 overlay instead.
DEFAULT_SCHEMA = FIXTURES / "schema_quirks.yaml"


def build(schema_dir=None, **ctx):
    """Return the with-schema setup (the on arm). `schema_dir` is the directory (or file) holding
    the schema-and-quirks overlay, analyst-side when testing a real analyst. It defaults to our
    canonical fixture so the setup is runnable hermetically. The off arm is baseline()."""
    spec = str(schema_dir) if schema_dir is not None else str(DEFAULT_SCHEMA)
    return Setup(name="with-schema", layer="L4", reader="file", spec=spec)


def baseline():
    """The no-schema arm: the bare baseline the with-schema arm is compared against. It stages no
    L4 content, so the agent has only column names and folklore to link against."""
    return Setup(name="no-schema", layer=None, reader="file", spec=None)


def compose_schema(overlays):
    """Merge schema overlays into one view (the tables, joins, and quirks the agent links
    against). This parallels compose_metrics for the L4 layer, which carries schema structure and
    quirks rather than a metrics list. Off-arm overlays are empty, so this returns empty lists and
    the toggle is visible as the difference between the two arms."""
    tables, joins, quirks = [], [], []
    for ov in overlays:
        ov = ov or {}
        tables.extend(ov.get("tables", []))
        joins.extend(ov.get("joins", []))
        quirks.extend(ov.get("quirks", []))
    return {"tables": tables, "joins": joins, "quirks": quirks}


register_setup(SetupSpec(
    key="B4-schema",
    layer="L4",
    status="buildable-now",
    summary="Stage the schema-and-quirks overlay on or off; measure drift / schema-linking errors.",
    blocked_on=None,
    source="C-store.md, FRAMEWORK_v0 §2 (L4 data infrastructure)",
    build=build,
))
