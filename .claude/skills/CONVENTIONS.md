# Skill conventions for the eval tool

These skills let a person drive the eval tool by talking to Claude, never by typing a terminal
command. Claude writes and runs the Python under the hood. Plain language, no em-dashes.

Shared rules every skill follows:

- Run from inside `~/projects/ai-analytics-evals` (the eval tool repo), so imports work with no
  path insert. The two agentic skills that need the live analyst (`/reliability`, `/compare`) run
  in `~/projects/ai-analyst-plus` instead, because that is where the analyst and its data live.
- Populate the registries before reading them:
  `from aievals.graders import _load; _load.load_all()` and
  `from aievals.setups import load_all as _sl; _sl()`.
- Never hardcode a result number. A gold is computed in SQL at eval time; a metric is defined by
  meaning. If a skill needs data, it uses the bundled fixtures or a connection the caller supplies.
- Be honest about status. If a unit is partial, blocked, or frontier, say so from its SetupSpec or
  the grader's blocked result; do not present a blocked check as a pass.
- Deterministic skills produce the same output given the same input. The agentic part (asking the
  analyst N times) belongs to `/reliability` and `/compare`, which a person runs live.
