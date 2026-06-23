#!/usr/bin/env python3
"""Tests for B5 query patterns / gold SQL (L4): the toggle MECHANISM, and the honest blocked status.

Hermetic: the toggle is exercised against a placeholder pattern YAML written to a temp dir (clearly
a test fixture, not a validated pattern), so no warehouse, network, or analyst repo is touched. The
test proves two things: the file-reader toggle stages a patterns dir on and off correctly, AND the
SetupSpec reports status "blocked" with a non-empty reason rather than silently pretending the
"with" side of the comparison exists. Run: python3 tests/test_b5_query_patterns.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.setups import b5_query_patterns as b5
from aievals.setups.base import registry

# A PLACEHOLDER pattern, clearly a test fixture, not a validated gold-SQL pattern. It exists only
# to prove the toggle stages a directory; it carries no result number, by design.
PLACEHOLDER_PATTERN = """\
# PLACEHOLDER test fixture, NOT a validated query pattern. Exists only to exercise the toggle.
pattern_id: placeholder-spine-question
question: a NovaMart spine question (placeholder)
sql_shape: SELECT ... FROM orders WHERE status = 'completed'
confidence: F  # F = unvalidated; a real curated pattern would be A (owner-reviewed + query-tested)
note: replace with a maintainer-seeded gold-SQL pattern before this unit unblocks
"""


def _patterns_dir():
    d = Path(tempfile.mkdtemp(prefix="b5_patterns_"))
    (d / "placeholder.yaml").write_text(PLACEHOLDER_PATTERN)
    return d


# ---- the toggle MECHANISM ------------------------------------------------------------------

def test_toggle_stages_a_patterns_dir_on():
    d = _patterns_dir()
    setup = b5.build(patterns_dir=d)
    assert setup.layer == "L4" and setup.reader == "file"
    overlays = setup.read_overlays()
    assert len(overlays) == 1
    assert overlays[0]["pattern_id"] == "placeholder-spine-question"
    # it is honestly a placeholder, not a validated pattern
    assert overlays[0]["confidence"] == "F"


def test_default_stages_the_seeded_verified_pattern():
    # the canonical "with" side now defaults to the bundled NovaMart-verified gold-SQL pattern
    setup = b5.build()
    overlays = setup.read_overlays()
    assert len(overlays) == 1
    patterns = overlays[0]["patterns"]
    assert patterns[0]["pattern"] == "checkout_conversion_rate"
    # the quirk guard is baked in, and no answer is stored (computed in SQL at eval time)
    assert "had_purchase" in patterns[0]["quirk_guard"]
    assert "2.91" not in str(overlays) and "%" not in str(overlays)
    # the explicit no-pattern baseline reads nothing
    base = b5.baseline()
    assert base.layer is None and base.read_overlays() == []


# ---- the honest partial status (fixture real, live proof pending) --------------------------

def test_spec_reports_partial_with_reason():
    spec = registry()["B5-query-patterns"]
    assert spec.status == "partial"             # fixture real and verified; live proof pending
    assert spec.blocked_on and spec.blocked_on.strip()
    assert "agentic run" in spec.blocked_on     # what actually remains
    assert "NovaMart-verified" in spec.blocked_on
    assert spec.layer == "L4"
    assert spec.source == "C-store.md"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b5_query_patterns:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
