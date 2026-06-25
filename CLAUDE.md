# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository. Plain language, no
em-dashes (the whole codebase has none; keep it that way).

## What this is

`ai-analytics-evals` is a standalone tool that tests an agentic analyst: does it answer reliably,
correctly, and with its work shown, and does a given piece of context actually move the answer. It
is built to public quality and ships open.

Two principles hold everywhere and are not negotiable:

- **The tool holds no credentials and no analyst-private path.** Knowledge and data live with the
  analyst. The tool reaches an analyst only through an adapter, and reaches data only through a
  connection the caller supplies. There is nothing to leak here.
- **No result number is ever hardcoded.** A metric is defined by its meaning; a gold answer is
  computed in SQL at eval time. If you ever find a literal answer baked into a module, that is a bug.

## The core idea

The instrument is the comparison run: hold the question, the model, and the data fixed, run the
same question two ways (with a piece of context and without it), and measure the delta. Every
validation check plugs into this as a grader. Every context-stack layer plugs in as a setup the
comparison run can toggle. Convergence is stability, not correctness: a wrong query can be
perfectly stable, so a self-consistency result is always a flag, never a correctness score.

## Layout

```
aievals/
  stats/reliability.py     deterministic stats over N runs (distinct, variance, agreement, verdict)
  harness/
    comparison.py          the comparison run: per-setup runs -> delta -> report
    setups.py              generalized setups: the L0-L6 layer vocabulary, Setup, source-readers
    run_meta.py            per-run quality, speed, tokens; cost computed from the model rate
    controls.py            validity controls: held-out split, model-pin, noise floor
    recall.py              the cheap context-recall precheck (did the answer cite the context)
  graders/
    base.py                the grader interface: six families, four intensity rungs, the selector
    a1_reliability.py ... a10_data_fitness.py   one grader per validation check
    _load.py               load_all(): import every grader so each self-registers
  setups/
    base.py                the SetupSpec registry with honest status labels
    b0_system.py ... b_topology.py              one module per context-stack setup
    fixtures/              the canonical meaning-only contract, the seeded correction and pattern
    __init__.py            load_all(): import every setup so each self-registers
  data/gold.py             GoldCase, compute_gold (SQL at eval time), schema_checksum
  adapters/
    base.py                AnalystAdapter (stage/run/restore), the model seam, the adapter registry
    ai_analyst_plus.py     the adapter for our private analyst
    ai_analyst_starter.py  registered but blocked on W1.3 (the repo does not exist yet)
  scorecard.py             C1: roll graders into one card, never additive across regimes
  pipeline.py              Track D: the six analysis pieces mapped to graders and setups
  campaign.py              E1: rank which context layers move the answer
tests/                     hermetic tests, runnable (python3 tests/test_x.py) and via pytest
tools/secret_scan.py       the pre-push gate that fails on any committed credential
.claude/skills/            the driving commands a person talks to (see below)
```

## Conventions you must follow

- **Graders** subclass `graders.base.Grader`, decorate with `@register`, and set name, family
  (one of the six in `FAMILIES`), truth_basis, surface, and cost_tier (the cheapest intensity at
  which they run; `heavy=True` for audit-only). `grade()` returns a `GraderResult` built with
  `self.result(...)`. A result is a `score` (lives in one regime) or a `flag` (surfaced, never
  summed). A check that cannot run returns status `blocked` with a `blocked_on` reason; it is never
  silently passed. The registry is self-declaring, so a new grader is a new file, not an edit to a
  central list.
- **Setups** register a `SetupSpec(key, layer, status, summary, blocked_on, source, build)` via
  `register_setup`. `status` is one of buildable-now, blocked, partial, frontier, described-only,
  and it is the honest truth carried in code. `build(**ctx)` returns a `Setup` (or a list) with no
  hardcoded analyst path; it defaults to the bundled fixture where one applies.
- **The producer is never the grader.** The adapter seam guarantees the thing that produced an
  answer does not grade it; the scorecard records this.
- **Honest labels everywhere.** buildable-now means it runs and is tested. partial, blocked, and
  frontier mean exactly what they say, and the test proves the blocked part reports blocked.
- **Locked rules:** methodology and decision are a flag, never a correctness score; realized-outcome
  scoring is gated on reconciled outcome pairs we do not have; judge scores are not trusted until
  calibrated; confidence is a deterministic tier with no number.

## Running and testing

- Full suite: `python3 -m pytest -q` (currently 193 tests). Any module's test also runs standalone:
  `python3 tests/test_<name>.py`, which prints ok lines and exits non-zero on failure.
- Secret gate before any push: `python3 tools/secret_scan.py <repo-path>`. Findings are redacted.
- Data libraries available: pandas, duckdb, snowflake.connector. The NovaMart practice DuckDB lives
  with the analyst at `~/projects/ai-analyst-plus/data/practice/`, not here.

## The driving skills (.claude/skills/)

A person drives the tool by talking to Claude, never by typing a terminal command; Claude runs the
Python under the hood. Deterministic skills run from this repo. The two agentic skills that ask the
live analyst N times, `/reliability` and `/compare`, run in `~/projects/ai-analyst-plus`, because
that is where the analyst and its data live. See `.claude/skills/CONVENTIONS.md`.

## Status and honest boundaries

What is built, partial, blocked, and frontier is recorded in
`~/projects/ai-analytics-for-builders/program-plan/BUILD-OUT-STATUS.md`, and the plan it instantiates
is `program-plan/BUILD-OUT-PLAN.md` in that repo. Short version: Layer 0, all ten graders, the
fifteen setups, the scorecard, the pipeline map, and the campaign are built and tested. The live
agentic-run proofs, judge calibration, realized-outcome scoring, the B-home Snowflake arm (blocked
on warehouse write access), the starter adapter (W1.3), and datasets beyond NovaMart are open and
labeled as such. Do not present any of those as done.
```
