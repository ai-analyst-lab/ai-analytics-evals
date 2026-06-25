---
name: check
description: Run one validation grader on an analysis output and explain what it caught. Use when the user says "/check", "run the <name> grader", "what does the provenance check say about this answer", "grade just the methodology", or wants to see a single check (A1-A10) in isolation rather than the whole scorecard. Each grader returns a per-surface result with its truth basis and a score or a flag, never a cross-regime number.
---

# Skill: Check (one grader at a time)

## Purpose
Show what a single validation check catches, on its own. This is the by-hand way to learn each
grader: run it on an output that should pass and one that should fail, and read the result. The
companion is `/scorecard`, which runs many graders into one card.

## Invocation
`/check <grader-name> on <output>`

The grader names are the registered ids: A1-reliability, A2-known-answer, A3-provenance,
A4-triangulation, A5-rubric-judge, A6-methodology, A7-decision, A8-execution, A9-confidence,
A10-data-fitness. If the user names a check loosely ("the reliability one"), map it to the id.

## How to run it
Run from `~/projects/ai-analytics-evals`. Populate the registry, fetch the grader, build the
output it reads, and call grade().

```python
from aievals.graders import _load, base as gb
_load.load_all()
GraderCls = gb.registry()["A1-reliability"]   # the id the user asked for
g = GraderCls()
result = g.grade(OUTPUT, intensity="decision-grade", run_type="single-number", **CTX)
print(result.as_dict())
```

What each grader reads from `OUTPUT` (and `CTX`), so you build the right shape:
- A1-reliability: `OUTPUT["runs"]` (the N run blocks). Returns a stability flag.
- A2-known-answer: `OUTPUT["headline"]` plus `gold=GoldCase(...)` and `conn=` a connection to
  recompute the gold in SQL. Use `aievals.data.gold` and a DuckDB connection for the bundled data.
- A3-provenance: `OUTPUT["footer"]` (a dict). Blocked footer fields are listed, never passed.
- A4-triangulation: `OUTPUT["arms"]` (each with a `direction`).
- A5-rubric-judge: `OUTPUT["narrative"]` plus `rubric=` and `judge=` a callable. The score is
  flagged uncalibrated until a labeled set exists; say so.
- A6-methodology: `OUTPUT["method"]` and `OUTPUT["question_type"]`. A flag, never a score.
- A7-decision: `OUTPUT["recommendation"]` and the analysis it should follow from. A flag; the
  realized-outcome part is gated and reports blocked.
- A8-execution: `OUTPUT["result_df"]` plus `expected_df=`. A partial-DataFrame match.
- A9-confidence: source tier, validation status, run count. A deterministic tier label, no number;
  the model self-report is ignored.
- A10-data-fitness: `OUTPUT["data_fitness"]` (or its absence). A flag; the fitness score is frontier.

## Present it
Show the grader id, its family and truth basis, whether it is a score or a flag, the status
(pass / fail / flag / blocked / not-applicable), and the one-line detail. If the result is blocked,
say what it is blocked on. Frame the lesson: this check catches X, and here is the boundary (for
A1, convergence is stability not correctness; for A5/A7, the trusted form is gated on calibration
or outcome pairs).
