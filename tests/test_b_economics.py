#!/usr/bin/env python3
"""Tests for B-economics: the resident-footprint measurement over run metadata.

Hermetic: no warehouse, no network, no analyst repo. The unit only reads RunMeta token counts,
so the tests construct RunMetas by hand and assert footprint_report ranks them and computes the
delta correctly, and that the SetupSpec carries its honest status (buildable-now, but build=None
because it measures rather than stages). Run: python3 tests/test_b_economics.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.harness.run_meta import RunMeta, cost_usd
from aievals.setups import b_economics as econ
from aievals.setups.base import SetupSpec


# ---- footprint_report: the core measurement ------------------------------------------------

def test_report_ranks_larger_context_and_computes_delta():
    # Two arms of the same comparison: a lean retrieved-tail run and a heavy load-everything run.
    lean = RunMeta(model="claude-opus-4-8", input_tokens=1500, output_tokens=200)
    heavy = RunMeta(model="claude-opus-4-8", input_tokens=40000, output_tokens=200)
    rep = econ.footprint_report([
        {"name": "retrieve-tail", "meta": lean},
        {"name": "load-everything", "meta": heavy},
    ])
    # per_setup preserves input order and carries each footprint
    names = [r["name"] for r in rep["per_setup"]]
    assert names == ["retrieve-tail", "load-everything"]
    by_name = {r["name"]: r for r in rep["per_setup"]}
    assert by_name["load-everything"]["footprint_tokens"] == 40000
    assert by_name["retrieve-tail"]["footprint_tokens"] == 1500
    # the delta names the heavy arm as the larger footprint and gets the gap right
    d = rep["delta"]
    assert d["heaviest"] == "load-everything"
    assert d["leanest"] == "retrieve-tail"
    assert d["footprint_delta"] == 40000 - 1500
    assert d["footprint_delta"] >= 0
    # honest: the report says footprint is a cost fact, not a quality verdict
    assert "not a quality verdict" in d["detail"]


def test_delta_is_order_independent():
    # Same two arms, heavy first: the report must still pick the larger footprint, not the first.
    lean = RunMeta(model="claude-opus-4-8", input_tokens=2000, output_tokens=100)
    heavy = RunMeta(model="claude-opus-4-8", input_tokens=9000, output_tokens=100)
    rep = econ.footprint_report([
        {"name": "heavy", "meta": heavy},
        {"name": "lean", "meta": lean},
    ])
    assert rep["delta"]["heaviest"] == "heavy"
    assert rep["delta"]["footprint_delta"] == 7000


def test_report_accepts_run_meta_dict_form():
    # meta may be a RunMeta or its as_dict() form; both must work.
    lean = RunMeta(model="claude-opus-4-8", input_tokens=1000, output_tokens=50).as_dict()
    heavy = RunMeta(model="claude-opus-4-8", input_tokens=5000, output_tokens=50).as_dict()
    rep = econ.footprint_report([
        {"name": "lean", "meta": lean},
        {"name": "heavy", "meta": heavy},
    ])
    assert rep["delta"]["footprint_delta"] == 4000


def test_report_carries_computed_cost_never_invents_it():
    # cost is the value RunMeta computed (or None for an unknown model); the report never guesses.
    known = RunMeta(model="claude-opus-4-8", input_tokens=1000, output_tokens=100)
    known.cost_usd = cost_usd("claude-opus-4-8", 1000, 100)
    unknown = RunMeta(model="mystery-model", input_tokens=2000, output_tokens=100)
    rep = econ.footprint_report([
        {"name": "known", "meta": known},
        {"name": "unknown", "meta": unknown},
    ])
    by_name = {r["name"]: r for r in rep["per_setup"]}
    assert by_name["known"]["cost_usd"] == cost_usd("claude-opus-4-8", 1000, 100)
    assert by_name["unknown"]["cost_usd"] is None


def test_single_or_empty_setup_has_no_delta():
    assert econ.footprint_report([])["delta"] is None
    one = econ.footprint_report([
        {"name": "solo", "meta": RunMeta(model="claude-opus-4-8", input_tokens=500)},
    ])
    assert one["delta"] is None
    assert one["per_setup"][0]["footprint_tokens"] == 500


def test_report_has_no_hardcoded_answer_number():
    # The footprint comes from the RunMeta the caller passes, not a literal baked into the module.
    src = Path(econ.__file__).read_text()
    for literal in ("55.4", "75.2", "84.8", "33.2"):
        assert literal not in src


# ---- the SetupSpec: honest status carried in code ------------------------------------------

def test_setup_spec_is_a_measurement_not_a_toggle():
    # the spec is registered at import; pull it from the registry by key
    from aievals.setups.base import registry
    reg = registry()
    assert "B-economics" in reg
    s = reg["B-economics"]
    assert isinstance(s, SetupSpec)
    assert s.layer is None                 # cross-cutting, not a single layer
    assert s.status == "buildable-now"     # the measurement works now
    assert s.build is None                 # there is nothing to stage; it measures
    assert s.source == "C-economics.md"
    assert "measurement" in s.summary.lower()


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b_economics:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
