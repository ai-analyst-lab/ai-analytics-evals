#!/usr/bin/env python3
"""Tests for the A3 provenance grader (family: inspection). Hermetic: no warehouse, no network,
no analyst repo. Inspects footer dicts only. Run: python3 tests/test_a3_provenance.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders.a3_provenance import (
    ProvenanceGrader, footer_check, BLOCKED_FIELDS, CONFIDENCE_TIERS,
)

# A footer carrying the fields the analyst actually emits today (W0.3): the object it read, a
# freshness date (MAX(date) of the rows), and a confidence tier. No result number anywhere.
GOOD_FOOTER = {
    "object": "novamart.analytics.orders",
    "freshness": "2026-06-17",
    "confidence": "green",
}


def test_good_footer_passes():
    g = ProvenanceGrader()
    res = g.grade({"footer": GOOD_FOOTER})
    assert res.kind == "score" and res.status == "pass" and res.value == 1.0
    # it is a presence verdict, and says the boundary out loud
    assert "auditable, not correct" in res.detail
    assert g.family == "inspection" and g.truth_basis == "presence" and g.surface == "footer"


def test_missing_freshness_fails():
    g = ProvenanceGrader()
    no_fresh = {"object": "novamart.analytics.orders", "confidence": "green"}
    res = g.grade({"footer": no_fresh})
    assert res.status == "fail" and res.value == 0.0
    assert "freshness" in res.detail


def test_malformed_freshness_fails():
    # present but not a date: presence alone is not enough, well-formedness is graded too
    bad = dict(GOOD_FOOTER, freshness="recently")
    res = ProvenanceGrader().grade({"footer": bad})
    assert res.status == "fail" and res.value == 0.0


def test_malformed_confidence_fails():
    bad = dict(GOOD_FOOTER, confidence="pretty sure")  # not a tier
    res = ProvenanceGrader().grade({"footer": bad})
    assert res.status == "fail" and res.value == 0.0


def test_no_footer_at_all_fails_not_passes():
    res = ProvenanceGrader().grade({"headline": "55.4%"})  # no footer key at all
    assert res.status == "fail" and res.value == 0.0
    assert "no receipt" in res.detail


def test_blocked_fields_are_listed_not_passed():
    # the W0.3 fields V-provenance names but the footer cannot emit yet must surface as
    # not-yet-checkable on a PASSING result, never silently counted as present/passed
    res = ProvenanceGrader().grade({"footer": GOOD_FOOTER})
    assert res.status == "pass"
    for field in BLOCKED_FIELDS:
        assert field in res.blocked_on, f"{field} should ride in blocked_on"
    assert "not-yet-checkable" in res.detail.lower()
    # and they are NOT in the present set: they were never graded as satisfied
    report = footer_check(GOOD_FOOTER)
    for field in BLOCKED_FIELDS:
        assert field not in report["present"]
    assert set(report["blocked"]) == set(BLOCKED_FIELDS)


def test_footer_check_separates_present_missing_malformed():
    report = footer_check(GOOD_FOOTER)
    assert set(report["present"]) == {"source", "freshness", "confidence"}
    assert report["missing"] == [] and report["malformed"] == []
    # source alias resolves either "source" or "object"
    alt = footer_check({"source": "x", "freshness": "2026-01-01", "confidence": "red"})
    assert "source" in alt["present"]


def test_confidence_tiers_accept_known_values():
    for tier in CONFIDENCE_TIERS:
        f = dict(GOOD_FOOTER, confidence=tier)
        assert ProvenanceGrader().grade({"footer": f}).status == "pass"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_a3_provenance:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
