# Exercise: triangulation (V9)

One observational question, answered through genuinely different methods, reduced to a decision
direction each, then reconciled. The question: **did the Summer Sale (July 1-14, 2024, 15% off,
everyone) increase NovaMart revenue?** No experiment exists for it, no control group, no answer key.
That is the point: if an experiment existed, you would just analyze the experiment.

## The three rules
1. **Same question to every arm.** Only the method changes.
2. **Fresh session per arm.** Clear between methods, and do not read `directions.csv` or any earlier
   analysis first. An arm that can see another arm's answer anchors on it.
3. **Direction, not number.** Each arm reduces to yes / no / unclear plus a one-line basis. The
   numbers will not match across methods and are not supposed to.

## Files
- `log_direction.py` — appends an arm's result to `directions.csv` (run_id, timestamp, method,
  direction, headline, basis). Answer first, log after.
- `directions.csv` — your grid, created on first log. Gitignored; it is your run.

Data access: the `connect-snowflake` skill in this repo (live NovaMart, read-only). The prompts for
each arm are in the student guide.

Two ways to run it:
- **Guided arms** (the student guide): three prescribed angles, one prompt each, fresh session per arm.
- **The orchestrator flow** (`ORCHESTRATOR.md`): one prompt picks four distinct approaches, runs three
  as parallel blind subagents, and hands the fourth to a different model family in a second terminal.
