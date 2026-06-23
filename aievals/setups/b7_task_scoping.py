"""B7 Task / session scoping (canonical layer L6): stage the live question and plan as context.

L6 is the session frame, the transient layer the other layers feed into: the live question, the
plan to answer it, the running conversation. It is not a stored home like a metric dictionary or a
schema. It is composed fresh for each task. So this unit carries its canonical content in the
module itself (a broad frame and a narrow frame) and surfaces it through the source-reader
interface, rather than reading it from a YAML home the way B3 reads a metric contract.

The point of the unit is to make the session frame a toggleable, comparable setup like every other
layer. The comparison run can stage the frame on or off, or swap a broad scope for a narrow one,
and measure whether scoping the task moves the answer. A broad frame ("how is retention doing")
leaves the agent to invent the window, the cohort, and the filters. A narrow frame pins the cohort,
the window, and the exclusions in the question and the plan, so the run has less room to wander.
Neither frame names a result: a frame scopes the QUESTION, never the ANSWER. The agent still
computes every figure from the data each run, so there is no hardcoded number anywhere here.

A real analyst can point this at their own session frames instead (reader="file", spec=<dir>), so
the eval tool holds no analyst path; the inline frames below are our canonical teaching default.
"""
from aievals.harness.setups import Setup, SourceReader, register_reader
from aievals.setups.base import SetupSpec, register_setup


# The two canonical session frames. Each scopes the live question and the plan to answer it. There
# is no result value in either frame, by design: a frame says what to ask and how to proceed, not
# what the figure is. The window and cohort below are scoping choices (like the contract's window),
# not answers.
BROAD_FRAME = {
    "session": {
        "scope": "broad",
        "question": "How is customer retention doing?",
        "plan": [
            "pull a retention number",
            "summarize whether it looks healthy",
        ],
    }
}

NARROW_FRAME = {
    "session": {
        "scope": "narrow",
        "question": (
            "For customers whose first completed order falls in a given month, what share placed "
            "a second completed order within ninety days, by first-purchase-month cohort?"
        ),
        "plan": [
            "group customers by first-purchase month",
            "keep completed orders only, drop internal and test accounts",
            "flag a cohort customer who placed a second completed order within ninety days",
            "divide flagged customers by the cohort size, per cohort month",
        ],
        "cohort": "first-purchase month",
        "window": "ninety days from each customer's first completed order",
        "filters": [
            "completed orders only (exclude cancelled and returned)",
            "exclude internal and test accounts",
        ],
    }
}


class FrameReader(SourceReader):
    """Surface an in-module session frame as composable overlays. The session frame (L6) is
    transient and composed per task, so its content travels with the run in `spec` rather than
    living in a file or warehouse home. `spec` is a frame dict, a list of frame dicts, or None
    (the off baseline, which yields no overlays)."""
    name = "frame"

    def read(self, spec):
        if spec is None:
            return []
        if isinstance(spec, dict):
            return [spec]
        return list(spec)


register_reader(FrameReader())


def _arm(scope, frame):
    """One task-scope arm: the named session frame staged at layer L6 via the frame reader."""
    return Setup(name=f"task-{scope}", layer="L6", reader="frame", spec=frame)


def build(scope=None, reader="frame", spec=None, **ctx):
    """Return the task-scope setup(s).

    With no arguments, returns both arms [narrow, broad] so the comparison run can swap one scope
    for the other and measure the delta. Pass scope="narrow" or scope="broad" for a single arm, or
    scope="off" for the no-frame baseline. To stage a real analyst's own session frames from a file
    home, pass reader="file" and spec=<dir of yaml>; the eval tool then holds no analyst path and
    the inline canonical frames are not used.
    """
    if reader == "file":
        return Setup(name=f"task-{scope or 'frame'}", layer="L6", reader="file", spec=spec)
    if scope == "off":
        return baseline()
    if scope == "narrow":
        return _arm("narrow", NARROW_FRAME)
    if scope == "broad":
        return _arm("broad", BROAD_FRAME)
    return [_arm("narrow", NARROW_FRAME), _arm("broad", BROAD_FRAME)]


def baseline():
    """The frame-off arm: no session frame staged, the bare baseline the narrow and broad arms are
    compared against. Layer is None and it reads no overlays."""
    return Setup(name="no-task-frame", layer=None, reader="frame", spec=None)


register_setup(SetupSpec(
    key="B7-task-scoping",
    layer="L6",
    status="buildable-now",
    summary="Stage the live question and plan (the session frame) on or off, or narrow vs broad.",
    blocked_on=None,
    source="FRAMEWORK_v0 §2 (L6 session/task)",
    build=build,
))
