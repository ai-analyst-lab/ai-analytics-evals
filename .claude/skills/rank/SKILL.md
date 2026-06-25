---
name: rank
description: Rank which context layers actually move the answer, across the whole grid, by aggregating the per-setup comparison deltas into one ordering. Use when the user says "/rank", "rank the context methods", "which layers are load-bearing", "which context is ceremony", "run the method-ranking campaign", or "resolve the granularity decision". A large delta ranks first; a delta below the noise floor is flagged "not distinguishable from noise," never sold as an effect. This is the campaign-scale form of the comparison run, run sampled and occasional, never every cohort.
---

# Skill: Rank (the method-ranking campaign)

## Purpose
Track B measures one setup at a time. The payoff is the ranking: across the whole context grid,
which layers are load-bearing and which are ceremony. This rolls the per-setup comparison deltas
into one ordering, with the validity controls in force so a real effect is told apart from run-to-run
noise. The companion checks are `/check` (one grader) and `/scorecard` (one analysis); this is the
campaign across many setups.

## Invocation
`/rank` (the campaign over the measured per-setup deltas), or `/rank --resolve-granularity` to
settle FRAMEWORK_v0 D1 (per-metric vs single-index vs domain-bundled) once all three arms exist.

The per-setup deltas come from Track B comparison runs (`/compare`, the user's live runs against the
analyst). This skill does the deterministic aggregation and ranking only.

## How to run it
Run from `~/projects/ai-analytics-evals`. Compute the noise floor from two baseline runs, then rank
the supplied per-setup deltas; nothing here is a hardcoded result.

```python
from aievals.campaign import rank_methods, resolve_granularity
from aievals.harness.controls import noise_floor

# Noise floor: the same baseline run twice (Track B supplies these from its real runs).
floor = noise_floor(
    [{"headline": "25.3%"}, {"headline": "25.4%"}],
    [{"headline": "25.3%"}, {"headline": "25.5%"}],
)

# Per-setup comparison deltas Track B measured one at a time; the campaign aggregates them.
setup_deltas = [
    {"setup": "L4-metric-contract", "delta": 0.74},
    {"setup": "L1-schema-card",     "delta": 0.31},
    {"setup": "L6-topology",        "delta": floor / 2},   # below the floor on purpose
    {"setup": "L2-glossary",        "delta": None},         # delta not measured yet
]
ranking = rank_methods(setup_deltas, floor)
print("noise floor:", floor)
for i, r in enumerate(ranking, 1):
    print(f"{i}. {r['setup']:20} delta={r['delta']}  -> {r['verdict']}")

# D1 (granularity) stays unresolved until all three arms are staged.
gran = resolve_granularity(
    [{"setup": "per-metric", "delta": 0.5}, {"setup": "single-index", "delta": 0.2}],
    floor,
)
print("D1 resolved:", gran['resolved'])
print("reason:", gran['reason'])
```

Replace the example deltas with the real Track B deltas (one per setup) and the floor with the real
baseline runs. The agentic part (asking the analyst N times to produce those deltas) belongs to
`/compare` and `/reliability`, which the user runs live.

## Present it
Read the ranking top to bottom: the largest distinguishable delta is the most load-bearing layer,
deltas below the floor read "not distinguishable from noise" (ceremony, not effect), and a missing
delta reads "undetermined." For `resolve_granularity`, report `resolved` and the `reason` verbatim:
D1 stays open until B-granularity stages all three arms (per-metric, single-index, domain-bundled),
and the skill says so rather than naming a winner it cannot back. Boundary: a ranking is only
trustworthy under the validity controls (a pinned model across arms, a held-out split, the noise
floor), and the campaign is sampled and occasional, never run on every cohort.
