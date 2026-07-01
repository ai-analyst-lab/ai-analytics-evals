# Exercise: build a chart judge (V8a)

You build an LLM-as-judge for charts from scratch, align it to a human golden set, and use it as a
target to improve a chart. Everything runs here in `ai-analytics-evals`. Charts are made with plain
matplotlib by prompting (we do NOT use ai-analyst-plus's SWD chart helpers, because those auto-apply
the good style and would make every chart pass). The data is the live 2024 NovaMart revenue, pulled by
`get_revenue.py` (no data is committed).

This is a hand-built version of the real judge that lives next door at
`aievals/graders/a5_rubric_judge.py` (the A5 rubric-judge): same idea, an `Axis` has a name, a pass
anchor, and a fail anchor; a `Rubric` is a set of axes; the score is per-axis pass/fail.

## Files
- `RUBRIC.md` — your judge's axes. You grow this one rule at a time. Mirrors A5's Axis shape.
- `judge.md` — the judge prompt (run blind: score, then log, do not read scores first).
- `get_revenue.py` — pulls the live 2024 monthly revenue (no committed data).
- `log_score.py` — appends a judge run to `scores.csv`, one row per axis (long format).
- `score_judge.py` — measures the judge against the golden set, precision/recall, appends `alignment-scores.csv`.
- `golden/` — 14 charts human-labeled pass/fail (`golden-labels.csv`), the answer key for alignment.
- `scores.csv` / `alignment-scores.csv` — your two run logs (created on first run).
- `submissions/` — where you drop your rubric and improving charts.

## The loop (phase 1: build the judge by improving a chart)
Make a first chart, then repeat, one rule per turn: add a rule to `RUBRIC.md`, judge the current chart
(blind, logs to `scores.csv`), expand the chart prompt to fix the flaw, judge the new chart. The chart
climbs toward good and the rubric grows into a real judge. See the student guide for the exact prompts.

## Phase 2: align the judge to the golden set
Run your judge over all 12 golden charts, feed its overall verdicts to `score_judge.py`, read
precision/recall, see which it fails, improve the rubric, re-run, watch alignment climb in
`alignment-scores.csv`.

## Phase 3 (optional): judge reliability
Run the judge several times on one chart. A stable, aligned judge is one you can lean on. Same idea as
the V1 reliability check, pointed at the judge.
