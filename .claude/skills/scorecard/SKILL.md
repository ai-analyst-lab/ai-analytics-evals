---
name: scorecard
description: Roll many graders into one scorecard for an analysis, at a chosen intensity. Use when the user says "/scorecard", "score this analysis", "grade the whole answer", "run the decision-grade checks", or wants the card rather than a single check. The card keeps present separate from correct, never sums across regimes, and the verdict is a label decided by correctness, so a clean footer never rescues a wrong number.
---

# Skill: Scorecard (the whole card at an intensity)

## Purpose
Run the checks the stakes call for, all at once, and present them honestly: present versus correct,
a coverage axis, and a single non-numeric verdict. This is where the intensity dial lives: the
same analysis runs one check at exploratory and the full set at audit-grade. The anti-gaming
tripwire is the point to feel: a garbage number with a perfect footer scores fail, not pass.

## Invocation
`/scorecard "<question>" --intensity <exploratory|operational|decision-grade|audit-grade>`

Default intensity is decision-grade. To show the dial, run the same output at two intensities and
compare how many checks ran.

## How to run it
Run from `~/projects/ai-analytics-evals`. Populate the registry, then score one analysis output.

```python
from aievals.graders import _load, registry
from aievals import scorecard as sc
_load.load_all()
graders = list(registry().values())
card = sc.score_analysis(QUESTION, OUTPUT, graders,
                         intensity="decision-grade", run_type="single-number", **CTX)
print(card.verdict())            # pass / fail / flag / incomplete (a label, never a number)
print(card.present_vs_correct()) # present checks vs correctness checks, kept apart
print(card.coverage())           # how many ran, how many checked, blocked, not-applicable
```

`OUTPUT` is the analysis to grade (headline, footer, runs, method, etc.); `CTX` carries what the
correctness graders need (for example `gold=` and `conn=` for A2, `expected_df=` for A8). Graders
whose inputs are absent return not-applicable or blocked, so the card stays honest about what it
could check.

## Show the two lessons
1. The intensity dial: run exploratory (one check) and audit-grade (the full set) on the same
   output and show the count change.
2. The anti-gaming tripwire: take an output with a wrong number and a perfect footer and show the
   verdict is fail, because correctness dominates presence. Set `propagation_ok=False` to show that
   a right number for the wrong question also scores fail.
