#!/usr/bin/env python3
"""Tests for B0 Model / system (canonical layer L0). Hermetic: builds two system-prompt arms from
temp directories of overlay yaml, no analyst repo and no network. Run: python3 tests/test_b0_system.py

What is proven here:
  - the system-prompt swap is buildable now: two arms staged from different temp dirs read back
    different system-prompt content, and each Setup records which prompt directory it used;
  - the model-swap arm is honestly partial: it reports status "partial" with a reason and hands
    back no runnable Setup, rather than silently running against one model twice;
  - the registered SetupSpec is buildable-now at layer L0 and notes the partial model arm.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml

from aievals.setups import b0_system as b0
from aievals.setups.base import SetupSpec


def _write_prompt(dir_path, text):
    """Write one system-prompt overlay yaml into dir_path and return the dir as a str."""
    p = Path(dir_path) / "system.yaml"
    p.write_text(yaml.safe_dump({b0.SYSTEM_PROMPT_KEY: text}))
    return str(dir_path)


# ---- system-prompt swap (buildable now) ----------------------------------------------------

def test_two_prompt_arms_stage_different_content():
    with tempfile.TemporaryDirectory() as da, tempfile.TemporaryDirectory() as db:
        text_a = "You are a careful analyst. State your assumptions before answering."
        text_b = "You are a fast analyst. Answer in one line."
        _write_prompt(da, text_a)
        _write_prompt(db, text_b)

        arm_a, arm_b = b0.build_arms(da, db)

        # each Setup records which prompt it was staged from (the spec differs)
        assert arm_a.spec != arm_b.spec
        assert arm_a.spec == str(da) and arm_b.spec == str(db)
        assert arm_a.layer == "L0" and arm_b.layer == "L0"
        assert arm_a.name == "prompt-A" and arm_b.name == "prompt-B"

        # and the staged content actually differs when read back through the file reader
        ov_a = arm_a.read_overlays()
        ov_b = arm_b.read_overlays()
        assert ov_a[0][b0.SYSTEM_PROMPT_KEY] == text_a
        assert ov_b[0][b0.SYSTEM_PROMPT_KEY] == text_b
        assert ov_a[0][b0.SYSTEM_PROMPT_KEY] != ov_b[0][b0.SYSTEM_PROMPT_KEY]


def test_build_default_is_the_bare_baseline_arm():
    # no prompt_dir means the agent's default system prompt: an L0 arm with no overlay to read
    arm = b0.build()
    assert arm.layer == "L0" and arm.spec is None
    assert arm.read_overlays() == []
    # the explicit baseline toggles nothing on, so its layer is None
    assert b0.baseline().layer is None


def test_build_takes_a_caller_path_no_hardcoded_path():
    with tempfile.TemporaryDirectory() as d:
        _write_prompt(d, "You are an analyst.")
        arm = b0.build(prompt_dir=d)
        assert arm.spec == str(d)
        assert arm.read_overlays()[0][b0.SYSTEM_PROMPT_KEY] == "You are an analyst."


# ---- model swap (partial until a second model is wired) ------------------------------------

def test_model_swap_arm_reports_partial_not_a_fake_setup():
    arm = b0.model_swap_arm(model="some-other-model")
    assert isinstance(arm, b0.PartialArm)
    assert arm.status == "partial"
    assert arm.setup is None                      # no runnable Setup is handed back
    assert "second" in arm.blocked_on.lower() or "0.5" in arm.blocked_on
    assert b0.MODEL_SWAP_STATUS == "partial"


# ---- registered SetupSpec ------------------------------------------------------------------

def test_setupspec_is_registered_buildable_now_at_L0():
    from aievals.setups.base import registry
    spec = registry()["B0-system"]
    assert isinstance(spec, SetupSpec)
    assert spec.layer == "L0"
    assert spec.status == "buildable-now"         # the prompt swap is runnable now
    assert spec.build is b0.build
    assert "partial" in spec.summary.lower()      # the model arm's honesty is noted


# ---- no hardcoded result numbers -----------------------------------------------------------

def test_module_carries_no_result_number():
    src = (ROOT / "aievals" / "setups" / "b0_system.py").read_text()
    # the only digits in the module are the layer/section markers (L0, §2, 0.5), never a result
    for banned in ("55.4", "75.2", "84.8", "33.2"):
        assert banned not in src


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b0_system:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
