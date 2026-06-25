---
name: footprint
description: Measure the resident token footprint of context and of skills, so "more context is not better past a point" and the turn-zero cost of a skill library become visible numbers. Use when the user says "/footprint", "how much context did that cost", "what is the token footprint", "measure the resident footprint", "what do my skills cost at turn zero", or wants the cost side of a context-rot story rather than a quality verdict. It reads RunMeta token counts (footprint_report) and skill descriptors (skills_footprint) and reports per-setup and per-skill resident tokens. It is a cost fact, never a quality verdict.
---

# Skill: Footprint (the resident token cost of context and of skills)

## Purpose
Make the cost side of context visible. Two measurements live here. The first reads each setup's
RunMeta and reports the resident token footprint per setup plus the delta between the lean arm and
the heavy arm, so "more context is not better past a point" becomes a number you put next to a
quality result. The second sums the turn-zero metadata of a skill or tool library (the descriptions
and non-deferred schemas resident in the prefix every turn), so the cost of the catalog is itemized.
Both are pure measurements: footprint is a cost fact, not a quality verdict.

## Invocation
`/footprint` (context footprint over runs, skills footprint over a descriptor list, or both)

## How to run it
Run from `~/projects/ai-analytics-evals`, no path insert. The footprint functions are plain
measurements over inputs you hand them, so no registry load is needed.

```python
from aievals.harness.run_meta import RunMeta, cost_usd
from aievals.setups.b_economics import footprint_report
from aievals.setups.b_skills import skills_footprint

# Context footprint: two setups' RunMeta token counts, lean vs heavy. Cost is computed, never guessed.
def meta(model, inp, out):
    m = RunMeta(model=model, input_tokens=inp, output_tokens=out)
    m.cost_usd = cost_usd(model, inp, out)
    return m

rep = footprint_report([
    {"name": "lean-context",  "meta": meta("claude-opus-4-8", 1200, 300)},
    {"name": "heavy-context", "meta": meta("claude-opus-4-8", 8400, 300)},
])
for row in rep["per_setup"]:
    print(row["name"], row["footprint_tokens"], "resident tokens, cost", row["cost_usd"])
d = rep["delta"]
print("delta:", d["footprint_delta"], "more resident tokens in", d["heaviest"], "vs", d["leanest"])

# Skills footprint: sum the turn-zero resident metadata tokens (descriptors carry real count_tokens reads).
skills = [{"name": "check", "tokens": 180}, {"name": "scorecard", "tokens": 210}, {"name": "footprint", "tokens": 95}]
fp = skills_footprint(skills)
print("skills footprint:", fp["total_tokens"], "tokens across", fp["skill_count"], "skills")
print("sums correctly:", fp["total_tokens"] == sum(b["tokens"] for b in fp["breakdown"]))
```

To measure real runs, pass the RunMetas the other B units recorded instead of the example metas; to
measure a real library, build the descriptors from a `count_tokens` reading of the live prefix, not
an eyeballed estimate.

## Present it
Read the larger context as the larger footprint: the heavy arm reports more resident tokens than the
lean arm, and the delta is that gap (never negative). For skills, show the per-skill breakdown and
confirm it sums to the total, so a builder sees which entries dominate the turn-zero budget. The
boundary: footprint is cost, not quality. A bigger footprint is not worse on its own; that verdict
only comes from reading this number next to a quality signal (A1 reliability, A2 known-answer) with
`/scorecard`. The descriptor tokens must come from a real `count_tokens` reading, not a guess, or the
skills number is not trustworthy.
