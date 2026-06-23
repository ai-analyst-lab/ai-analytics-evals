#!/usr/bin/env python3
"""Tests for B-granularity: the three structural forms of the retention definition (Menu C / D1).

Hermetic: stages the three forms into a temp directory from the canonical retention contract, no
warehouse, no network, no analyst repo. Proves (1) each of the three granularities stages and
restores, (2) a reader can tell them apart because the staged structures genuinely differ, (3) the
meaning is held fixed across forms, and (4) none of them contains a result number.
Run: python3 tests/test_b_granularity.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.setups import b_granularity as bg
from aievals.setups.base import registry, STATUSES
from aievals.harness.setups import compose_metrics


def _arms():
    """Build the three arms into a fresh temp dir and return them."""
    return bg.build(staging_dir=tempfile.mkdtemp(prefix="bg_test_"))


# ---- each granularity stages and restores --------------------------------------------------

def test_three_arms_each_stage_the_same_metric():
    arms = _arms()
    assert [a.name for a in arms] == list(bg.STRUCTURES)
    for arm in arms:
        overlays = arm.read_overlays()
        metrics = compose_metrics([], overlays)
        names = [m["metric"] for m in metrics]
        assert "retention_rate" in names, f"{arm.name} did not stage retention_rate"
        assert arm.layer == "L3"  # layer held fixed across arms; only structure varies


def test_baseline_restores_to_nothing():
    # restore = the no-granularity baseline stages no overlay, so composing yields only the base
    base = bg.baseline()
    assert base.layer is None
    assert compose_metrics([], base.read_overlays()) == []


# ---- a reader can tell the three structures apart -------------------------------------------

def test_structures_are_distinguishable_on_disk():
    arms = {a.name: a for a in _arms()}
    per_metric = arms[bg.PER_METRIC].spec
    single = arms[bg.SINGLE_INDEX].spec
    bundled = arms[bg.DOMAIN_BUNDLED].spec
    # the spec SHAPES differ: a directory, a single file, an explicit list (the on-demand load)
    assert Path(per_metric).is_dir()
    assert Path(single).is_file()
    assert isinstance(bundled, list) and Path(bundled[0]).is_file()
    # the three specs are not the same object/value
    assert len({str(per_metric), str(single), str(bundled)}) == 3


def test_each_overlay_names_its_own_structure():
    arms = {a.name: a for a in _arms()}
    seen = set()
    for label, arm in arms.items():
        overlays = arm.read_overlays()
        markers = {(ov or {}).get("structure") for ov in overlays}
        assert markers == {label}, f"{label} overlay structure marker mismatch: {markers}"
        seen |= markers
    # all three structural labels are distinct and present
    assert seen == set(bg.STRUCTURES) and len(seen) == 3


def test_domain_bundle_is_on_demand_and_per_metric_is_per_area():
    arms = {a.name: a for a in _arms()}
    bundle_ov = arms[bg.DOMAIN_BUNDLED].read_overlays()[0]
    assert bundle_ov["load"] == "on-demand" and bundle_ov["domain"] == bg.DOMAIN
    pm_ov = arms[bg.PER_METRIC].read_overlays()[0]
    assert pm_ov["area"] == bg.AREA


# ---- meaning is held fixed across the three forms ------------------------------------------

def test_meaning_is_identical_across_forms():
    arms = _arms()
    contracts = []
    for arm in arms:
        metrics = compose_metrics([], arm.read_overlays())
        rr = next(m for m in metrics if m["metric"] == "retention_rate")
        # compare the meaning-bearing fields, not the structural wrapper
        contracts.append((rr.get("means"), rr.get("numerator"),
                          rr.get("denominator"), rr.get("window")))
    assert contracts[0] == contracts[1] == contracts[2]
    assert all(c[0] for c in contracts)  # means is actually present, not empty


# ---- no result number anywhere -------------------------------------------------------------

def test_no_form_contains_a_result_number():
    for arm in _arms():
        blob = str(arm.read_overlays())
        # the meaning is defined without a computed figure: no percent, no known measured literals
        assert "%" not in blob, f"{arm.name} leaked a percent sign"
        for lit in ("55.4", "84.8", "75.2", "33.2"):
            assert lit not in blob, f"{arm.name} leaked result literal {lit}"


# ---- honest registration -------------------------------------------------------------------

def test_registered_buildable_now_and_cross_cutting():
    spec = registry()["B-granularity"]
    assert spec.status == "buildable-now" and spec.status in STATUSES
    assert spec.layer is None  # cross-cutting axis, not a single layer
    assert spec.blocked_on is None
    assert "D1" in spec.source and "CONTEXT-DECISION-GRID" in spec.source


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b_granularity:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
