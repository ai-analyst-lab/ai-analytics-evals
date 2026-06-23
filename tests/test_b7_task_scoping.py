#!/usr/bin/env python3
"""Tests for B7 task / session scoping (canonical layer L6). Hermetic: the frame content lives in
the module, and the file-home path is exercised with a temp YAML file, so there is no analyst repo,
no warehouse, and no network. Run: python3 tests/test_b7_task_scoping.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.setups import b7_task_scoping as b7
from aievals.setups.base import registry


# ---- the two arms stage different content --------------------------------------------------

def test_narrow_and_broad_stage_different_content():
    arms = b7.build()                          # defaults to [narrow, broad]
    assert isinstance(arms, list) and len(arms) == 2
    narrow = next(a for a in arms if a.name == "task-narrow")
    broad = next(a for a in arms if a.name == "task-broad")
    no = narrow.read_overlays()
    bo = broad.read_overlays()
    # both arms live at L6 and both produce a frame, but the staged content differs
    assert narrow.layer == "L6" and broad.layer == "L6"
    assert no and bo and no != bo
    nq = no[0]["session"]["question"]
    bq = bo[0]["session"]["question"]
    assert nq != bq
    # the narrow frame pins cohort, window, and filters that the broad frame leaves open
    assert "cohort" in no[0]["session"] and "cohort" not in bo[0]["session"]
    assert len(no[0]["session"]["plan"]) > len(bo[0]["session"]["plan"])


def test_single_arm_selection():
    narrow = b7.build(scope="narrow")
    broad = b7.build(scope="broad")
    assert narrow.name == "task-narrow" and narrow.layer == "L6"
    assert broad.name == "task-broad" and broad.layer == "L6"
    assert narrow.read_overlays() != broad.read_overlays()


def test_frame_off_baseline_stages_nothing():
    base = b7.baseline()
    assert base.layer is None                  # no layer staged
    assert base.read_overlays() == []          # the off arm reads no overlays
    assert b7.build(scope="off").read_overlays() == []


# ---- a frame scopes the question, never the answer (no hardcoded result) --------------------

def test_frames_carry_no_result_number():
    blob = str(b7.NARROW_FRAME) + str(b7.BROAD_FRAME)
    # a frame names what to ask and how, not the figure: no percentage answer anywhere
    assert "%" not in blob
    for token in ("55.4", "84.8", "75.2", "33.2"):
        assert token not in blob


# ---- the file home is supported so the tool holds no analyst path ---------------------------

def test_file_reader_home_is_hermetic():
    with tempfile.TemporaryDirectory() as d:
        frame_yaml = Path(d) / "frame.yaml"
        frame_yaml.write_text(
            "session:\n"
            "  scope: narrow\n"
            "  question: analyst-supplied scoped question\n"
            "  plan:\n"
            "    - step one\n"
        )
        setup = b7.build(reader="file", scope="narrow", spec=d)
        assert setup.layer == "L6" and setup.reader == "file"
        overlays = setup.read_overlays()
        assert overlays and overlays[0]["session"]["scope"] == "narrow"


# ---- the SetupSpec is registered with its honest status ------------------------------------

def test_setup_registered_buildable_now():
    spec = registry()["B7-task-scoping"]
    assert spec.layer == "L6"
    assert spec.status == "buildable-now"      # buildable now: staging the task frame works
    assert spec.blocked_on is None             # nothing blocks it
    assert spec.build is b7.build
    # the builder it points to actually produces a runnable L6 setup
    assert b7.build(scope="narrow").layer == "L6"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b7_task_scoping:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
