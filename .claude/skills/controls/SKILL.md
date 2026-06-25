---
name: controls
description: Run the three validity controls that make a comparison trustworthy before you believe a "this context moved the answer" result. Use when the user says "/controls", "check the validity controls", "is this comparison held out", "is the model pinned", "what is the noise floor", or "is this delta real or just noise". The controls are guards, not graders: a held-out check refuses an eval set that overlaps the context-tuning set, a model-pin check refuses arms that ran on different models, and a noise floor from two baseline runs marks a sub-noise delta as not distinguishable from noise.
---

# Skill: Controls (the guards on a comparison)

## Purpose
A comparison delta is only trustworthy if three things hold: the eval set is held out from the
context-tuning set, both arms ran on one pinned model, and the delta clears the run-to-run noise
floor. This skill runs all three guards and reports which ones refuse. A refusal is the point: it
stops you crediting memorization, a silent model swap, or noise as a context effect.

## Invocation
`/controls` on a comparison (its context ids, eval ids, arm model ids, and two baseline runs).

## How to run it
Run from `~/projects/ai-analytics-evals`. The controls are pure functions, so no registry load is
needed; supply the comparison's own ids and runs.

```python
from aievals.harness.controls import (
    assert_held_out, assert_model_pinned, noise_floor, distinguishable, ValidityError)

# 1. Held-out: the eval set must not overlap the context-tuning set.
context_ids = ["q1", "q2", "q3"]   # questions used to tune the context
eval_ids    = ["q3", "q4", "q5"]   # questions we grade on (q3 overlaps)
try:
    assert_held_out(context_ids, eval_ids)
    print("held-out: PASSED (no overlap)")
except ValidityError as e:
    print("held-out REFUSED:", e)

# 2. Model-pin: both arms of a comparison must run on one pinned model.
arms = [{"model": "claude-x"}, {"model": "claude-y"}]
try:
    assert_model_pinned(arms)
    print("model-pin: PASSED (one model)")
except ValidityError as e:
    print("model-pin REFUSED:", e)

# 3. Noise floor: a delta smaller than the baseline-to-baseline spread is not an effect.
baseline_a = [{"headline": "25.0%"}, {"headline": "25.4%"}]   # baseline run 1
baseline_b = [{"headline": "25.0%"}, {"headline": "25.6%"}]   # baseline run 2 (same condition)
floor = noise_floor(baseline_a, baseline_b, metric="cv")
sub_noise_delta = floor * 0.5            # an observed delta below the floor
print("noise floor (cv):", floor)
print("sub-noise delta distinguishable?:", distinguishable(sub_noise_delta, floor))
```

## Present it
Report each guard as passed or refused. For held-out and model-pin, a refusal is a `ValidityError`
and the message names exactly what overlapped or which models differed; do not let the comparison
proceed when either refuses. For the noise floor, print the floor and whether the delta clears it:
`distinguishable()` returns False for a sub-noise delta and None when a stat is missing, which the
caller reports as not-distinguishable rather than an effect. The boundary: the model-pin check needs
a selectable model id (Layer 0.5), so on arms that did not record a model it refuses with "the pin
cannot be verified" rather than passing. Held-out and the noise floor stand on their own. These
controls guard the comparison; the live N-times comparison itself is the user's run under
`/compare` in `~/projects/ai-analyst-plus`.
