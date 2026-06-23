#!/usr/bin/env python3
"""Tests for B-skills: the turn-zero resident-footprint measurement. Hermetic: pure arithmetic over
descriptors, no warehouse, no network, no analyst repo. Run: python3 tests/test_b_skills.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.setups import b_skills
from aievals.setups.base import registry


# A small resident set: skill descriptions plus one non-deferred tool schema, with their turn-0
# token costs supplied by the caller (these are inputs, not a result the module invents).
RESIDENT = [
    {"name": "north-star", "tokens": 80},
    {"name": "metric-contract", "tokens": 96},
    {"name": "run_snowflake_query", "tokens": 310},
]


# ---- the footprint measurement --------------------------------------------------------------

def test_footprint_sums_tokens_and_reports_breakdown():
    fp = b_skills.skills_footprint(RESIDENT)
    # total is exactly the sum of the per-skill tokens (computed, not hardcoded)
    assert fp["total_tokens"] == sum(s["tokens"] for s in RESIDENT)
    assert fp["skill_count"] == len(RESIDENT)
    # the breakdown itemizes every entry in input order, so a builder sees which dominates
    assert fp["breakdown"] == [{"name": s["name"], "tokens": s["tokens"]} for s in RESIDENT]
    # the tool schema is the heaviest resident entry here
    heaviest = max(fp["breakdown"], key=lambda b: b["tokens"])
    assert heaviest["name"] == "run_snowflake_query"


def test_empty_resident_set_is_zero_footprint():
    fp = b_skills.skills_footprint([])
    assert fp["total_tokens"] == 0 and fp["skill_count"] == 0 and fp["breakdown"] == []


def test_footprint_tracks_resident_set_not_catalog():
    # The thesis: footprint grows with what is RESIDENT, not with the catalog. Adding a deferred
    # skill (zero resident tokens until matched) does not move the total.
    deferred = RESIDENT + [{"name": "deep-research", "tokens": 0}]
    base = b_skills.skills_footprint(RESIDENT)
    bigger_catalog = b_skills.skills_footprint(deferred)
    assert bigger_catalog["total_tokens"] == base["total_tokens"]
    assert bigger_catalog["skill_count"] == base["skill_count"] + 1


def test_footprint_rejects_bad_descriptors():
    try:
        b_skills.skills_footprint([{"name": "x"}])  # missing tokens
        assert False, "expected ValueError for missing tokens"
    except ValueError:
        pass
    try:
        b_skills.skills_footprint([{"name": "x", "tokens": -5}])  # negative cost
        assert False, "expected ValueError for negative tokens"
    except ValueError:
        pass
    try:
        b_skills.skills_footprint(None)
        assert False, "expected TypeError for None"
    except TypeError:
        pass


# ---- the registered SetupSpec ---------------------------------------------------------------

def test_b_skills_registers_as_buildable_measurement_axis():
    spec = registry()["B-skills"]
    assert spec.status == "buildable-now"
    assert spec.layer is None            # cross-cutting axis, not a context layer to toggle
    assert spec.build is None            # a measurement, nothing to stage on/off
    assert "C-skills-context.md" in spec.source
    assert "footprint" in spec.summary.lower()


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b_skills:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
