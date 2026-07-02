# The orchestrator flow (the team of analysts)

One prompt turns your session into the analytics lead of a four-analyst team: it picks four
methodologically distinct approaches to the question, sends three of them to parallel subagents (each
one blind, a fresh context that sees nothing but its own assignment), and writes the fourth as a
self-contained prompt you paste into a DIFFERENT model in a second terminal (the same glm-5.2:cloud
you benchmarked on the Models day, via ollama). Different model family, different failure modes, which
is exactly the independence this check wants.

Before a fresh run: delete `directions.csv` and `arm4-prompt.txt` if they exist, so the grid you read and the prompt you paste are this run's only.

## The orchestrator prompt (paste in Claude Code, in this folder)

> You are the analytics lead on a four-analyst team answering one question: did the Summer Sale
> (July 1-14, 2024, 15% off, all users) increase NovaMart revenue?
>
> 1. Pick FOUR methodologically distinct analysis approaches with different blind spots. Make them
> genuinely different kinds of comparison (for example: time-window comparisons, trend or counterfactual
> projections, attribution the way a marketing dashboard reads it, cohort or segment views, post-period
> checks). At least two of the four should NOT be from that example list, pick something the examples made you think of. Before assigning any approach, check the data can support it (this dataset has no prior-year history, so year-over-year style comparisons come back unclear). Name each approach and say in one line what its blind spot is.
>
> 2. Assign approaches 1-3 to three subagents run IN PARALLEL. Each subagent is blind: it gets only the
> question, its assigned approach, and the connect-snowflake skill for data access. It must not read
> directions.csv or any other analysis. Each subagent returns: its method in one line, the key numbers,
> and a direction (yes / no / unclear) with a one-line basis, then logs it with log_direction.py. Read
> log_direction.py's usage yourself first and put the exact command and flags in each subagent's brief,
> so the subagents never open any file in this folder.
>
> 3. For approach 4, first pull the data it needs yourself (keep it compact: daily completed revenue
> May 1 to August 14, and the promo's dates and discount). Then write a fully self-contained prompt
> containing the question, that data, and the instruction to analyze it with approach 4 and answer
> yes / no / unclear with a one-line basis. Save it to arm4-prompt.txt. Do not run it, it goes to a
> different model.
>
> 4. When the three subagents return, show me the grid: four rows (three arms plus a placeholder for
> arm 4), each with method, direction, basis.

## Arm 4, the second model (second terminal)

    ollama run glm-5.2:cloud

Paste the contents of `arm4-prompt.txt`. When it answers, come back to Claude Code and log it:

> "Log arm 4: method=<what it used>, direction=<yes|no|unclear>, basis=<its one-line basis>."

If you did not set up ollama on the Models day, run arm 4 through any second model you have access
to, or as a fourth subagent (you lose the different-model-family diversity but keep the method diversity).
