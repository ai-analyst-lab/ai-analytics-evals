"""B-topology Context topology across many agents (cross-cutting axis, layer=None): isolated runs
versus a shared definition spine.

When you fan one question ("why is checkout conversion down this month?") into several sub-runs
(by segment, by source table, by time window), the engineering choice that governs reliability is
how context flows across those sub-runs: isolate each one in its own fresh window, or share a
common spine between them. The field actively disagrees on the general answer (Anthropic argues
isolate, Cognition argues share, 48 hours apart), so this unit does not pick a winner. It builds
the one resolution that holds for analytics: isolate the work, share the definitions. Each sub-run
explores on its own, but every sub-run reads the SAME small validated definition spine, so they
diverge on method and converge on meaning. That is what takes isolated retention runs from a 9-99%
spread to agreement (one shared empirical anchor, the LL1 reliability demo, not three).

What is buildable now is the toggle this unit ships: the shared-spine arm stages one shared L3
contract that every sub-run references, and the isolated arm stages nothing shared, so a comparison
run can measure what injecting the spine does to inter-run divergence. What is NOT built here is the
full multi-agent topology: the higher rungs (role-specialized sub-agents on the spine, multi-model
on the spine) and the per-framework injection mechanics (LangGraph shared state, CrewAI read-only
scope, OpenAI handoff filters, AutoGen system messages) are frontier, designed but not run on our
stack. That honesty is carried in code: the SetupSpec status is "partial" and the higher rungs are
labelled "frontier" in RUNGS, so a caller never mistakes the toggle for the whole topology.

The build carries no analyst-private path (the caller supplies the directory the shared contract
lives in, or omits it to use our canonical retention fixture) and no result number (the spine is
meaning-only; every sub-run computes its figure from the data).

Source: book/research/C-topology.md (section 3, the shared-definition-spine build; section 3.3 rungs).
"""
from aievals.harness.setups import Setup
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup


def shared_spine(n_runs=3, contract_dir=None, **ctx):
    """The shared-definition-spine arm: `n_runs` isolated sub-runs that ALL read one shared L3
    contract. Returns a list of Setups, one per sub-run, every one pointing at the SAME spine
    `spec`, so the sub-runs are independent in their work but identical in the meaning they share.

    `contract_dir` is the directory holding the shared contract YAML (analyst-side when testing a
    real analyst); it defaults to our canonical fixture dir so the arm is runnable hermetically.
    The spine reaches every sub-run identically by construction: the same spec string is handed to
    each Setup, which is the "the spine must reach every isolated agent identically" requirement
    from C-topology section 3.2.
    """
    if n_runs < 1:
        raise ValueError(f"n_runs must be at least 1; got {n_runs}")
    spec = str(contract_dir) if contract_dir is not None else str(FIXTURES)
    return [Setup(name=f"subrun-{i}", layer="L3", reader="file", spec=spec) for i in range(n_runs)]


def isolated(n_runs=3, **ctx):
    """The isolated arm: `n_runs` sub-runs each on its own, with NO shared definition staged. Each
    Setup carries layer=None and spec=None, so nothing shared reaches the sub-runs and each one is
    free to invent the metric its own way. This is the bare baseline the shared-spine arm is
    compared against, and it is where the 9-99% retention spread comes from."""
    if n_runs < 1:
        raise ValueError(f"n_runs must be at least 1; got {n_runs}")
    return [Setup(name=f"subrun-{i}", layer=None, reader="file", spec=None) for i in range(n_runs)]


# The rungs from C-topology section 3.3 (simple to robust), with the honest build status of each
# carried in code. Rungs 1 to 3 are the buildable toggle this unit ships (a single agent, parallel
# isolated runs with no spine, and isolated runs plus the shared definition spine). Rungs 4 and 5
# (role-specialized sub-agents on the spine, and multi-model on the spine) plus the per-framework
# injection mechanics are frontier: designed in the research but not built or measured on our stack.
RUNGS = (
    {"rung": 1, "name": "single agent", "status": "buildable-now"},
    {"rung": 2, "name": "parallel isolated runs (no spine)", "status": "buildable-now"},
    {"rung": 3, "name": "isolated + shared definition spine", "status": "buildable-now"},
    {"rung": 4, "name": "role-specialized sub-agents on the spine", "status": "frontier"},
    {"rung": 5, "name": "multi-model on the spine", "status": "frontier"},
)


register_setup(SetupSpec(
    key="B-topology",
    layer=None,
    status="partial",
    summary="Isolated sub-runs versus a shared definition spine: shared_spine() stages one L3 "
            "contract every sub-run reads; isolated() stages nothing shared. Measure inter-run "
            "divergence with the spine on versus off.",
    blocked_on="full multi-agent topology is frontier; the shared-spine vs isolated toggle is "
               "buildable (rungs 1-3); rungs 4-5 and per-framework injection are not built",
    source="C-topology.md (section 3 shared-definition-spine; section 3.3 rungs)",
    build=shared_spine,
))
