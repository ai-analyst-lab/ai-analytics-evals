# ai-analytics-evals

The standalone eval tool behind the book. It tests whether you can trust an AI analysis, and
it does it for any analyst on any warehouse, not just ours. You use it by talking to Claude
Code in plain language; you never type a terminal command.

## What it does

The core move is a comparison run: ask the same question two ways, under different setups (for
example, with a metric definition and without it), and measure the delta. The setup whose
presence collapses a wide spread to one stable number is the context that moves the answer.

It measures three things on every run: quality (did the answers agree, did they match a known
answer), speed (how long, start to finish), and usage (tokens). Cost is computed from tokens
and the model rate, not chased. No result number is ever hardcoded; results are computed and
saved.

## How it is wired

The tool never touches data or knowledge directly. It talks to an analyst through a small
adapter (the one way in). Knowledge and data live with the analyst.

- `aievals/stats/` the deterministic statistics, shared with the plain reliability check so the
  two never disagree on the math.
- `aievals/harness/` the comparison run: compute the per-setup stats and the delta, write the
  report. Analyst-agnostic.
- `aievals/adapters/` one bridge per analyst. `ai_analyst_plus.py` drives our analyst;
  `base.py` is the interface a new adapter implements.
- `aievals/runs/` timestamped run directories and the audit log.
- `tests/` proves the math end to end on the real first-run values.

## Status

Early. The comparison math, the shared stats, and the ai-analyst-plus adapter's staging are
built and tested. The live run step (asking the analyst n times) is the reliability skill in
ai-analyst-plus today; the adapter points at it. Graders, the scorecard, dataset loaders, and
the judge come with their build waves. See `program-plan/` in the ai-analytics-for-builders
repo for the plan and the wave tracker.

## A run, end to end

1. Stage the no-definition setup, ask the question n times (the reliability skill), record the runs.
2. Stage the with-definition setup, ask again, record.
3. The comparison harness reads both and writes one report: the before and after, and whether
   the definition moved the answer.

Built to public quality. It declares no warehouse drivers and holds no credentials; those live
only with the analyst.
