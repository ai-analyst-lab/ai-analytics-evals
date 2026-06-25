---
name: freshness
description: Catch stale context before it is applied. Use when the user says "/freshness", "is this context still fresh", "did the schema change under my stored context", "run the staleness guard", or wants to prove the schema-diff guard catches a renamed or dropped column. Context built against a schema that has since changed is stale and must be quarantined, never loaded. Returns a deterministic stale / fresh decision from real schema checksums, no result number.
---

# Skill: Freshness (the staleness guard)

## Purpose
Every other context layer makes the store richer; this one keeps it true. The reliability thesis
(an agent's answer is governed by its context) collapses the moment the stored context drifts from
reality and nobody notices: a column gets renamed upstream, the stored schema fact still names the
old column, and the agent writes confident SQL against a column that no longer exists. The guard
binds a checksum of the schema a context entry was built against, recomputes it against the live
schema, and if they differ the context is stale and gets quarantined instead of loaded.

## Invocation
`/freshness` (run the bundled demo) or `/freshness on <connection> for <tables>` to check real
context against a live warehouse the caller supplies.

## How to run it
Run from `~/projects/ai-analytics-evals`. Make the checksums real against an in-memory DuckDB, then
call `detect_stale` for a changed schema and an identical one. No analyst path, no hardcoded number.

```python
import duckdb
from aievals.data.gold import schema_checksum
from aievals.setups.b_freshness import detect_stale, demo_schema_change
from aievals.setups import load_all as _sl
_sl()
from aievals.setups.base import registry as _setups
spec = _setups()["B-freshness"]
print("setup B-freshness status:", spec.status)

conn = duckdb.connect(":memory:")
conn.execute("CREATE TABLE orders (id INTEGER, customer INTEGER, net_revenue DECIMAL)")
context_checksum = schema_checksum(conn, ("orders",))                  # checksum at context-build time

same = schema_checksum(conn, ("orders",))                             # nothing changed
print("identical schema  detect_stale:", detect_stale(context_checksum, same))

conn.execute("ALTER TABLE orders RENAME COLUMN net_revenue TO net_rev_v2")
live = schema_checksum(conn, ("orders",))                            # the column moved
print("changed schema    detect_stale:", detect_stale(context_checksum, live))
conn.close()

res = demo_schema_change()                                           # self-contained inject-and-catch
print("demo action:", res["action"], "| stale:", res["stale"])
```

## Show it
Read the two `detect_stale` lines: an identical schema is `False` (fresh, safe to load) and a
changed schema is `True` (stale, quarantine the dependent entries and refuse rather than load). The
demo line should read `quarantine | stale: True`, the guard catching the injected rename from real
checksums, not a stipulated one. Name the boundary plainly: only the deterministic schema-diff guard
is buildable now. The full lifecycle machinery (freshness budgets and trust grades, proposed to
verified gating, bitemporal supersession and the conflict ladder, value-distribution drift for silent
redefinition, and the schema-fact to natural-language propagation hop) is frontier; the SetupSpec
status reads `partial` and `spec.blocked_on` lists exactly what is not yet built. The live analyst
arm (does the agent actually fail on the renamed column) is the user's run under `/reliability` or
`/compare` in `~/projects/ai-analyst-plus`.
