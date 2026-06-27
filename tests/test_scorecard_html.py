#!/usr/bin/env python3
"""Tests for aievals.scorecard_html: render one analysis's scorecard (the V5 confidence read) as
HTML with the four lanes kept apart, the confidence read prominent, and a what-to-fix list. The
lanes are never summed into one number. Hermetic. Run: python3 tests/test_scorecard_html.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.scorecard_html import render_scorecard_html, LANES

SAMPLE = {
    "question": "What is completed revenue for May?",
    "lanes": {
        "query_match":  {"status": "pass", "similarity": 0.94, "approved_query_ref": "gold-revenue-12"},
        "consistency":  {"status": "flag", "spread": "25.3%-25.4% over 5 runs"},
        "provenance":   {"status": "pass", "fields": ["source", "freshness", "confidence"]},
        "query_checks": {"status": "fail", "issues": ["joined order_items then SUM(total_amount)"]},
    },
    "confidence": "investigate",
    "what_to_fix": [
        "Resolve the fan-out: aggregate orders before joining line items.",
        "Re-run consistency after the fix.",
    ],
}


def _render(card):
    out = os.path.join(tempfile.mkdtemp(), "scorecard.html")
    return Path(render_scorecard_html(card, out)).read_text()


def test_has_four_lanes():
    doc = _render(SAMPLE)
    for _key, label, _fields in LANES:
        assert label in doc, f"lane {label} missing from HTML"
    assert len(LANES) == 4


def test_lane_statuses_and_fields_render():
    doc = _render(SAMPLE)
    assert "0.940" in doc                      # query_match similarity formatted
    assert "gold-revenue-12" in doc            # approved_query_ref
    assert "25.3%-25.4% over 5 runs" in doc    # consistency spread
    assert "source, freshness, confidence" in doc  # provenance fields
    assert "joined order_items then SUM(total_amount)" in doc  # query_checks issue


def test_confidence_read_prominent():
    doc = _render(SAMPLE)
    assert "Investigate" in doc
    assert 'class="read"' in doc
    # act and abstain map to their words too
    assert "Act" in _render(dict(SAMPLE, confidence="act"))
    assert "Abstain" in _render(dict(SAMPLE, confidence="abstain"))


def test_what_to_fix_listed():
    doc = _render(SAMPLE)
    assert "Resolve the fan-out: aggregate orders before joining line items." in doc
    assert "Re-run consistency after the fix." in doc


def test_lanes_not_summed():
    doc = _render(SAMPLE)
    # the card states the lanes are kept apart and not added
    assert "not added into one score" in doc
    # no single rolled-up numeric score is presented; the read is the verb, not a number
    assert "overall score" not in doc.lower()


def test_empty_fixes_says_nothing_flagged():
    doc = _render(dict(SAMPLE, what_to_fix=[]))
    assert "Nothing flagged." in doc


def test_shares_monitor_look():
    doc = _render(SAMPLE)
    assert doc.startswith("<!doctype html>")
    assert ".card{" in doc and "#d97706" in doc


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_scorecard_html:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
