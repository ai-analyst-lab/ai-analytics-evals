"""B0 Model / system (canonical layer L0): the agent plus its system prompt.

L0 is the bottom of the Context Stack: the model itself and the system prompt it runs under.
Two things can be swapped at this layer, and they are not equally ready, so this unit keeps them
honestly separate.

The system-prompt swap is buildable now. A system prompt is just another overlay the file reader
can stage, so the comparison run can stage prompt A, run, stage prompt B, run, and measure whether
a wording change (for example, telling the agent to state its assumptions) moves reliability. The
builder returns a Setup pointed at a directory of system-prompt overlay yaml, with no hardcoded
analyst path: the caller supplies the directory, or omits it to get the agent's default system
prompt (no overlay) as the baseline arm.

The model swap is not ready. Toggling between two models needs Layer 0.5 (a second wired model in
the adapter), which does not exist yet. Rather than return a fake arm that silently runs against
one model twice, the model-swap path reports status "partial" and names what it is blocked on, so a
caller asking for the model arm gets the blocker in code, not a misleading green run.
"""
from dataclasses import dataclass

from aievals.harness.setups import Setup
from aievals.setups.base import SetupSpec, register_setup

# The overlay key a system-prompt overlay yaml carries. One name, so the staging side and any
# reader agree on where the prompt text lives.
SYSTEM_PROMPT_KEY = "system_prompt"

# The model-swap arm is partial until a second model is wired (Layer 0.5). Carried in code, not
# only in a doc, so the honesty travels with the function that would build the arm.
MODEL_SWAP_STATUS = "partial"
MODEL_SWAP_BLOCKED_ON = (
    "Layer 0.5 (a second wired model in the adapter) does not exist yet, so a model swap would run "
    "against one model twice. Buildable once a second model is wired."
)


def build(prompt_dir=None, name="system-prompt", **ctx):
    """Return the system-prompt arm at layer L0. `prompt_dir` is the directory holding the
    system-prompt overlay yaml (the caller supplies it); omit it to get the agent's default system
    prompt (no overlay, spec=None) as the baseline arm. No hardcoded analyst path."""
    spec = str(prompt_dir) if prompt_dir is not None else None
    return Setup(name=name, layer="L0", reader="file", spec=spec)


def build_arms(prompt_a_dir, prompt_b_dir, **ctx):
    """Return the two system-prompt arms (prompt A vs prompt B) the comparison run toggles. Each
    arm records which prompt directory it was staged from, so the run can tie a result back to the
    prompt that produced it."""
    return [
        build(prompt_dir=prompt_a_dir, name="prompt-A"),
        build(prompt_dir=prompt_b_dir, name="prompt-B"),
    ]


def baseline():
    """The bare baseline: the agent's default system prompt with no L0 overlay staged. layer is
    None because nothing is being toggled on."""
    return Setup(name="default-system-prompt", layer=None, reader="file", spec=None)


@dataclass
class PartialArm:
    """An arm that cannot be staged yet. Carries the honest status and the reason in blocked_on, so
    a caller gets the blocker in code instead of a Setup that would silently run wrong. `setup`
    stays None until the blocker is cleared."""
    status: str
    blocked_on: str
    setup: object = None


def model_swap_arm(model=None, **ctx):
    """The model-swap arm. Partial until Layer 0.5 wires a second model: returns a PartialArm that
    reports status "partial" and names the blocker, and carries no runnable Setup. It does not
    silently fall back to the current model."""
    return PartialArm(status=MODEL_SWAP_STATUS, blocked_on=MODEL_SWAP_BLOCKED_ON, setup=None)


register_setup(SetupSpec(
    key="B0-system",
    layer="L0",
    status="buildable-now",
    summary=("Swap the system prompt (buildable now, staged as an overlay) or the model "
             "(model-swap arm is partial until a second model is wired, Layer 0.5)."),
    blocked_on=None,
    source="FRAMEWORK_v0 §2",
    build=build,
))
