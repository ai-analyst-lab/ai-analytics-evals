#!/usr/bin/env python3
"""Tests for B6 corrections (canonical layer L5): the toggle MECHANISM, and the honest blocked
status. Hermetic: the with-corrections arm is staged against a placeholder correction written to a
temp directory, so no analyst repo, no warehouse, and no network are touched. The test proves two
things at once: the staging mechanism works (toggle a corrections dir on and off), and the unit
reports itself as honestly blocked on the real seeded fixture rather than silently passing.
Run: python3 tests/test_b6_corrections.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.setups import b6_corrections as b6
from aievals.setups.base import registry, register_setup, SetupSpec

# A placeholder correction: procedural memory about how to query retention correctly. It carries a
# rule and a query shape, never a result number, by design. This is NOT the real seeded fixture (a
# correction tied to a reproducible NovaMart mistake); it exists only to exercise the toggle.
PLACEHOLDER_CORRECTION = """\
corrections:
  - id: CORR-PLACEHOLDER
    status: proposed
    type: procedural
    description: retention was computed with the wrong denominator (all-time users, not the cohort)
    fix: use the cohort active-in-period denominator, not all-time users
    sql_after: "-- group customers by first-purchase month, divide returners by cohort size"
"""


def _staged_corrections_dir():
    """Write a placeholder correction YAML into a fresh temp dir and return that dir. The caller is
    responsible for keeping the TemporaryDirectory alive while reading."""
    tmp = tempfile.TemporaryDirectory()
    (Path(tmp.name) / "log.yaml").write_text(PLACEHOLDER_CORRECTION)
    return tmp


# ---- the toggle mechanism ------------------------------------------------------------------

def test_toggle_stages_a_corrections_dir():
    tmp = _staged_corrections_dir()
    try:
        on = b6.build(corrections_dir=tmp.name)
        assert on.layer == "L5" and on.reader == "file"
        overlays = on.read_overlays()
        corrections = b6.compose_corrections(overlays)
        ids = [c["id"] for c in corrections]
        assert "CORR-PLACEHOLDER" in ids
        # a correction is procedural memory, not an answer: no result number is staged anywhere
        blob = str(overlays)
        assert "%" not in blob
    finally:
        tmp.cleanup()


def test_off_arm_stages_nothing_and_default_stages_the_seeded_correction():
    off = b6.baseline()
    assert off.layer is None
    assert b6.compose_corrections(off.read_overlays()) == []
    # the default build now stages the bundled NovaMart-verified correction (the had_purchase Q4 bug)
    default = b6.compose_corrections(b6.build().read_overlays())
    assert len(default) == 1
    assert "had_purchase" in default[0]["mistake"]
    # it is procedural memory (a rule and a fix), not a result number to recall
    assert "55.4" not in str(default)


def test_toggle_is_visible_as_the_difference_between_arms():
    tmp = _staged_corrections_dir()
    try:
        on = b6.compose_corrections(b6.build(corrections_dir=tmp.name).read_overlays())
        off = b6.compose_corrections(b6.baseline().read_overlays())
        assert len(on) == 1 and len(off) == 0
    finally:
        tmp.cleanup()


# ---- the honest partial status (fixture real, live proof pending) --------------------------

def test_setupspec_reports_partial_with_a_reason():
    spec = registry()["B6-corrections"]
    assert spec.status == "partial"
    assert spec.layer == "L5"
    assert spec.blocked_on and "NovaMart-verified" in spec.blocked_on
    # what remains is the live behavioral proof, not a missing fixture
    assert "agentic run" in spec.blocked_on
    assert "C-memory.md" in spec.source


def test_blocked_status_must_be_a_valid_status():
    # a typo in the status would be rejected at construction, proving the label is real, not free text
    try:
        register_setup(SetupSpec(key="_tmp", layer="L5", status="not-a-status"))
        raised = False
    except ValueError:
        raised = True
    assert raised


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b6_corrections:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
