"""B-freshness Freshness / lifecycle (canonical layer L4): keep the stored context true over time.

Every other context unit makes the store richer. This one is the only thing that keeps it true.
The reliability thesis (an agent's answer is governed by its context) collapses the moment the
context drifts from reality and nobody notices: a column gets renamed upstream, the stored schema
fact and the corrections that lean on it still reference the old name, and the agent generates
confident SQL against a column that no longer exists. The fix from C-lifecycle.md section 4 is the
deterministic schema-diff guard, the highest-ROI piece of the lifecycle and the one that needs no
ML: bind a checksum of the schema a context entry was built against, recompute it against the live
schema at session start, and if they differ the context is stale and must be quarantined rather
than loaded.

This module ships the part that is buildable now: the guard itself (detect_stale), a self-contained
demo that injects a schema change and shows the guard catches it, and the staged-context setup the
comparison run toggles. The honest status is "partial": the full lifecycle machinery (per-asset
freshness budgets and trust grades, proposed -> verified gating, bitemporal supersession and the
conflict-resolution ladder, value-distribution drift for silent redefinition, and the schema-fact
to natural-language propagation hop) is frontier and named in the SetupSpec, not papered over.

There is no result number anywhere here. The checksums are computed from a real schema at eval time
(reusing aievals.data.gold.schema_checksum); staleness is a property of the schema, never a literal.
"""
from aievals.data.gold import schema_checksum
from aievals.harness.setups import Setup
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup


def detect_stale(context_schema_checksum, live_schema_checksum):
    """The guard. True when the context was built against a schema that has since changed (stale,
    quarantine it), False when the two checksums agree (fresh, safe to load). Pure and
    deterministic: it compares two checksums and nothing else, so it never guesses."""
    return context_schema_checksum != live_schema_checksum


def live_schema_checksum(conn, tables):
    """Recompute the checksum of the named tables against the live connection the caller hands in.
    A thin wrapper over the gold helper so the guard speaks the same checksum vocabulary as the
    SQL-gold layer. The eval tool embeds no credential and no analyst path: it is given a
    connection (a local DuckDB file or the analyst's warehouse) and reads the schema through it."""
    return schema_checksum(conn, tables)


def guard(conn, tables, *, context_checksum):
    """Consumer-side schema-diff guard (C-lifecycle.md section 4). Recompute the live schema
    checksum for the tables a context entry depends on, compare it to the checksum bound when the
    entry was written, and decide: quarantine (do not load, route to the owner) when they differ,
    load when they agree. Returns a dict carrying both checksums so the decision is auditable, not
    asserted."""
    live = live_schema_checksum(conn, tables)
    stale = detect_stale(context_checksum, live)
    return {
        "stale": stale,
        "context_checksum": context_checksum,
        "live_checksum": live,
        "action": "quarantine" if stale else "load",
        "detail": (
            "schema changed under the stored context; quarantine the dependent entries to RED "
            "and refuse or flag rather than load"
            if stale else
            "live schema matches the schema the context was built against; safe to load"
        ),
    }


def demo_schema_change(conn=None, table="orders", column="net_revenue", renamed="net_rev_v2"):
    """The buildable demo (C-lifecycle.md section 6, injection step). Bind the checksum a context
    entry was built against, inject a realistic breaking change (rename the column the entry
    depends on), recompute the live checksum, and run the guard. Returns the guard result so a
    caller can see the guard catch the injected change.

    If `conn` is None a tiny in-memory DuckDB orders table is created so the demo is self-contained
    and hermetic; pass a connection to run it against real practice data or a warehouse. The
    checksums are real (computed from the schema), so the demo proves the catch rather than
    stipulating it."""
    own = conn is None
    if own:
        import duckdb
        conn = duckdb.connect(":memory:")
        conn.execute(f"CREATE TABLE {table} (id INTEGER, customer INTEGER, {column} DECIMAL)")
    try:
        bound = live_schema_checksum(conn, (table,))                  # checksum at context-build time
        conn.execute(f"ALTER TABLE {table} RENAME COLUMN {column} TO {renamed}")  # the injection
        return guard(conn, (table,), context_checksum=bound)         # live checksum now differs
    finally:
        if own:
            conn.close()


def build(contract_dir=None, **ctx):
    """Return the two comparison arms the freshness run toggles: the SAME stored L4 context run
    against a fresh warehouse versus one whose schema has drifted. The content is identical (both
    point at the worked retention contract); only the live schema differs, which is exactly what
    the guard detects. `contract_dir` is the directory holding the context YAML (analyst-side when
    testing a real analyst); it defaults to our canonical fixture so the setup is runnable
    hermetically with no analyst path baked in."""
    spec = str(contract_dir) if contract_dir is not None else str(FIXTURES)
    fresh = Setup(name="fresh-context", layer="L4", reader="file", spec=spec)
    stale = Setup(name="stale-context", layer="L4", reader="file", spec=spec)
    return [fresh, stale]


register_setup(SetupSpec(
    key="B-freshness",
    layer="L4",
    status="partial",
    summary=(
        "The schema-diff guard (detect_stale) and the inject-a-change demo are buildable now: a "
        "changed schema is caught deterministically and quarantined. The full lifecycle machinery "
        "(freshness budgets and trust grades, proposed->verified gating, bitemporal supersession "
        "and the conflict ladder, value-distribution drift, schema-fact to prose propagation) is "
        "frontier."
    ),
    blocked_on=(
        "full lifecycle machinery is frontier: freshness/grading, the verified gate, supersession "
        "and conflict resolution, value-distribution drift (silent redefinition), and the "
        "schema-fact to natural-language propagation hop are designed only, not yet built or run "
        "(see C-lifecycle.md sections 1-3, 5-6)"
    ),
    source="C-lifecycle.md",
    build=build,
))
