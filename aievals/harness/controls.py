"""Validity controls: no comparison result is trustworthy without these.

Three guards, so a measured "this context moved the answer" is real and not an artifact:

  held-out split   the context store must NOT be the eval store. If the questions you grade on
                   are the ones you tuned the context on, you measure memorization, not help.
                   assert_held_out() refuses an overlap.
  pinned model     one fixed model id across both arms of a comparison, so a silent model update
                   is never credited to a context change. assert_model_pinned() refuses a
                   comparison whose arms ran on different models.
  noise floor      run the baseline twice and measure the run-to-run spread; a delta smaller than
                   that floor is "not distinguishable from noise," not an effect.

The model-pin check needs a selectable model id (Layer 0.5); held-out and the noise floor stand
on their own.
"""
from aievals.stats.reliability import compute


class ValidityError(ValueError):
    """Raised when a comparison violates a validity control and its result cannot be trusted."""


def assert_held_out(context_question_ids, eval_question_ids):
    """Refuse a comparison whose eval questions overlap the questions used to tune the context."""
    overlap = sorted(set(context_question_ids) & set(eval_question_ids))
    if overlap:
        shown = overlap[:5]
        raise ValidityError(
            f"held-out violation: {len(overlap)} question(s) are in BOTH the context store and "
            f"the eval set (for example {shown}). The context store must not be the eval store.")
    return True


def assert_model_pinned(setups):
    """setups: a list of dicts, each with a 'model' key (the model id its runs used). Refuse a
    comparison whose arms did not all run on the same pinned model."""
    models = {s.get("model") for s in setups}
    if None in models:
        raise ValidityError(
            "model-pin: at least one arm did not record its model id, so the pin cannot be verified.")
    if len(models) > 1:
        raise ValidityError(
            f"model-pin violation: arms ran on different models {sorted(models)}; a delta cannot be "
            "attributed to context when the model also changed.")
    return True


def noise_floor(baseline_runs_a, baseline_runs_b, metric="cv"):
    """The run-to-run spread of the SAME baseline, run twice. Returns the floor: the absolute
    difference in the chosen stat between two independent baseline runs. A measured effect must
    exceed this floor to count. None if the stat is unavailable (no parseable numbers)."""
    a = compute(baseline_runs_a).get(metric)
    b = compute(baseline_runs_b).get(metric)
    if a is None or b is None:
        return None
    return round(abs(a - b), 4)


def distinguishable(delta, floor):
    """Is an observed delta above the noise floor? None (unknown) when either is missing, so the
    caller reports it as not-distinguishable rather than claiming an effect."""
    if delta is None or floor is None:
        return None
    return abs(delta) > floor
