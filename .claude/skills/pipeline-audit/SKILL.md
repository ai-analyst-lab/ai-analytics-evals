---
name: pipeline-audit
description: Walk a real analysis one piece at a time (the six pipeline pieces) and show, per piece, which validation graders fire on the detect side and which context setups feed the supply side, with the per-intensity check counts. Use when the user says "/pipeline-audit", "audit the pipeline", "what checks fire at each piece", "show the six pieces", "which context feeds the query piece", or wants the per-piece detect-and-supply map rather than one grader (/check) or one card (/scorecard). The map is deterministic; auditing a live analysis is agentic and hands to /scorecard per piece.
---

# Skill: Pipeline audit (the six pieces, detect and supply)

## Purpose
Show that a real analysis is six pieces, and that each piece triggers its own checks on the detect
side (Track A graders) and its own context on the supply side (Track B setups), at a depth set by
the intensity dial. This is the second axis of the tool: not "which check" but "where in the
analysis does each check belong." The honest headline is that only piece 3 (the metric definition)
is a proven detect-and-fix loop today; the other five are sourced how-to until the build measures
them on NovaMart.

## Invocation
`/pipeline-audit` (the whole map) or `/pipeline-audit piece <n>` for one piece, with an optional
`--intensity <exploratory|operational|decision-grade|audit-grade>`.

## How to run it
Run from `~/projects/ai-analytics-evals`. The map lives in `aievals.pipeline`; the setup statuses
come from the Track B registry so the supply side carries its honest label, not just a key.

```python
from aievals import pipeline as P
from aievals.setups import load_all as _sl, base as _sb
_sl()
status = {k: s.status for k, s in _sb.registry().items()}

print("spine question:", P.SPINE_QUESTION)
print("endpoints pull most (on average):", P.endpoints_pull_most())
for p in P.PIECES:
    loop = "proven loop" if p.proven else "sourced how-to"
    print(f"\npiece {p.n}: {p.name}  [{loop}]")
    print("  detect:", ", ".join(p.detect))
    print("  supply:", ", ".join(f"{k}({status.get(k, '?')})" for k in p.supply))
    print("  per-tier checks:", p.per_tier)

for n in (3, 6):
    print(f"\npiece {n} tier counts:",
          {tier: P.checks_for(n, tier)
           for tier in ("exploratory", "operational", "decision-grade", "audit-grade")})
```

## Present it
Read it as a map, not a verdict. Per piece, name the detect graders (the checks that fire), the
supply setups with their honest status (a `partial` setup like B5 query-patterns or B6 corrections
is a seed, not a fully runnable supply yet), and how the check count climbs with intensity. Call the two
research patterns: context concentrates at the endpoints (pieces 1 and 6 pull the most setups on
average), and the loop (detect, fix with context, re-check) is meant to run on every piece.

The boundary: this map is deterministic, but auditing a live analysis against it is agentic. Only
piece 3 is a proven detect-and-fix loop today (ask twice, cite the contract, recompute the gold in
SQL); the other five are sourced how-to. To actually run a piece on a real output, hand it to
`/scorecard` at the matching intensity (that is the user's live run), and never present a sourced
piece as a measured pass.
