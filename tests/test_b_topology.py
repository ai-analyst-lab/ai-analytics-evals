#!/usr/bin/env python3
"""Tests for B-topology: isolated runs versus a shared definition spine.

Hermetic: no warehouse, no network, no analyst repo. The shared-spine arm reads our canonical
retention fixture (or a temp YAML the caller supplies), the isolated arm reads nothing. Imports the
unit directly (not via load_all), so it does not depend on the rest of the suite being mid-write.
Run: python3 tests/test_b_topology.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import aievals.setups.b_topology as bt
from aievals.setups.base import registry
from aievals.harness.setups import compose_metrics


# ---- the shared-spine arm: one shared definition referenced by every sub-run -----------------

def test_shared_spine_stages_one_shared_definition_for_all_subruns():
    arm = bt.shared_spine(n_runs=4)               # defaults to our canonical fixture dir
    assert len(arm) == 4                          # genuinely multiple sub-runs
    # every sub-run points at the SAME spine spec: one shared definition, not four private ones
    assert len({s.spec for s in arm}) == 1
    assert all(s.spec is not None for s in arm)
    assert all(s.layer == "L3" for s in arm)      # the spine rides the meaning (sharing) axis
    # and every sub-run actually reads the shared contract back
    for s in arm:
        metrics = compose_metrics([], s.read_overlays())
        assert "retention_rate" in [m["metric"] for m in metrics]


def test_shared_spine_is_meaning_only_no_result_number():
    arm = bt.shared_spine()
    blob = str(arm[0].read_overlays())
    # the spine constrains what to count, never carries the answer the agent must compute
    assert "55.4" not in blob and "%" not in blob


# ---- the isolated arm: nothing shared --------------------------------------------------------

def test_isolated_arm_stages_no_shared_definition():
    arm = bt.isolated(n_runs=4)
    assert len(arm) == 4
    assert all(s.spec is None for s in arm)       # nothing staged
    assert all(s.layer is None for s in arm)      # no shared layer reaches the sub-runs
    assert all(s.read_overlays() == [] for s in arm)


def test_two_arms_differ_on_the_shared_spine():
    shared = bt.shared_spine()
    iso = bt.isolated()
    # the toggle is visible as exactly this difference: spine present vs absent
    assert shared[0].spec is not None and iso[0].spec is None


# ---- no hardcoded analyst path: the caller supplies the contract dir --------------------------

def test_caller_supplied_contract_dir_reaches_every_subrun():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "contract.yaml").write_text(
            "metrics:\n"
            "  - metric: activation_rate\n"
            "    means: share of signups who reach first value\n"
        )
        arm = bt.shared_spine(n_runs=3, contract_dir=d)
        assert len({s.spec for s in arm}) == 1    # still one shared spine, now the caller's
        for s in arm:
            names = [m["metric"] for m in compose_metrics([], s.read_overlays())]
            assert names == ["activation_rate"]   # reads the caller's dir, not a baked-in path


def test_empty_run_count_rejected():
    for bad in (0, -1):
        try:
            bt.shared_spine(n_runs=bad)
            assert False, "expected ValueError for n_runs < 1"
        except ValueError:
            pass


# ---- honest status carried into code: partial, not silently buildable ------------------------

def test_spec_reports_partial_with_frontier_reason():
    spec = registry()["B-topology"]
    assert spec.status == "partial"               # not "buildable-now": the full topology is frontier
    assert spec.layer is None                     # a cross-cutting axis, not one L0-L6 layer
    assert spec.blocked_on and "frontier" in spec.blocked_on
    assert spec.build is bt.shared_spine          # the buildable arm is wired as the build


def test_higher_rungs_marked_frontier_not_built():
    by_rung = {r["rung"]: r["status"] for r in bt.RUNGS}
    assert by_rung[3] == "buildable-now"          # isolated + shared spine: the toggle we ship
    assert by_rung[4] == "frontier"               # role-specialized sub-agents: not built
    assert by_rung[5] == "frontier"               # multi-model on the spine: not built


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b_topology:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
