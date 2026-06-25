---
name: recall
description: The cheap context-recall precheck, run before paying for a full comparison. Use when the user says "/recall", "did the answer even cite the context", "is this worth a comparison run", "check recall before /compare", or wants to know whether a staged context fired before spending runs on it. Recall under 100% means the context was present but did not fire (a supply bug, context staged but not read), not a model bug, so the comparison gate stays shut.
---

# Skill: Recall (the cheap context-recall precheck)

## Purpose
Before paying for a full with-and-without comparison, check the leading indicator: did the answer
even cite the toggled context? If the runs never cite it, recall is below 100% and the finding
would be a supply bug (context present, did not fire), not a context effect. So this gate nominates
only the setups worth a full comparison. The companions are `/compare` and `/reliability`, which
spend the real runs once the gate opens.

## Invocation
`/recall on <the N run blocks under a staged context>`

The runs are the per-run blocks the analyst emits; each carries its citation in `definition_source`
(the receipts substrate) or `citations`. The marker is the substring that marks a citation of the
toggled context (for a metric definition, `dictionary`).

## How to run it
Run from `~/projects/ai-analytics-evals`. Score one set of runs that cite the context (gate opens)
and one set that ignore it (gate stays shut).

```python
from aievals.harness import recall

# A set where every run cited the metric dictionary: full recall, the gate opens.
cited = [{"definition_source": "metric dictionary: active_user = ..."} for _ in range(5)]
fired = recall.context_recall(cited)
print(fired, "-> run comparison?", recall.should_run_comparison(fired))

# A set where the runs inferred from columns and never read the context: gate stays shut.
ignored = [{"definition_source": "inferred from column names"} for _ in range(5)]
miss = recall.context_recall(ignored)
print(miss, "-> run comparison?", recall.should_run_comparison(miss))

# Partial recall (3 of 5 cited): present but did not fire on every run, still a supply bug.
partial = recall.context_recall(cited[:3] + ignored[:2])
print(partial, "-> run comparison?", recall.should_run_comparison(partial))
```

## Present it
For each set, read `recall` (the fraction that cited the context), `fired` (did it cite at all),
and `full_recall` (did it cite on every run), then the gate from `should_run_comparison`. The
lesson: only the full-recall set opens the gate. The ignored set and the partial set both stay
shut, because the context did not fire on every run.

The boundary: this is a supply check, not a correctness check. Full recall only means the context
was read, not that it changed the answer or that the answer is right. The gate is the hard
dependency on emission: it can only read a citation the analyst actually emits, so a missing
`definition_source` reads as a miss. When the gate opens, hand the real measurement to `/compare`
or `/reliability` in `~/projects/ai-analyst-plus`, which the user runs live against the analyst.
