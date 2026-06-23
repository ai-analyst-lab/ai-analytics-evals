#!/usr/bin/env python3
"""Tests for B1c: the company / org glossary setup (canonical layer L1) and the L1-vs-L3 precedence
resolver. Hermetic: no warehouse, no network, no analyst repo. Staging reads committed teaching
fixtures and a temp file; the resolver runs on plain dicts. Run: python3 tests/test_b1c_company_glossary.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.setups import b1c_company_glossary as b1c
from aievals.setups import b3_metric_definition as b3
from aievals.setups.base import registry


# ---- the setup: glossary on / off ----------------------------------------------------------

def test_glossary_on_stages_terms_off_stages_nothing():
    on = b1c.build()                      # defaults to the canonical fixture (the on arm)
    off = b1c.baseline()                  # the off arm
    on_overlays = on.read_overlays()
    off_overlays = off.read_overlays()
    # on stages real glossary content; off stages nothing; the two arms differ
    assert off_overlays == []
    assert on_overlays != off_overlays
    terms = [t["term"] for ov in on_overlays for t in (ov or {}).get("glossary", [])]
    assert "retention_rate" in terms
    # the glossary is the L1 layer; the baseline touches no layer
    assert on.layer == "L1" and off.layer is None
    # meaning-only: the glossary carries no result figure anywhere (no percentage answer)
    blob = str(on_overlays)
    assert "%" not in blob and "55.4" not in blob


def test_glossary_staged_from_any_home():
    # build() takes a path via ctx and holds no hardcoded analyst location: a temp dir works
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "glossary.yaml"
        p.write_text("glossary:\n  - term: active_customer\n    means: a customer\n    layer: L1\n")
        staged = b1c.build(glossary=d).read_overlays()
    terms = [t["term"] for ov in staged for t in (ov or {}).get("glossary", [])]
    assert terms == ["active_customer"]


# ---- the L1-vs-L3 precedence resolver ------------------------------------------------------

def test_area_l3_beats_company_l1_on_conflict():
    # equal recency, so the deciding rung is source authority: area L3 over company L1
    l1 = {"term": "retention_rate", "layer": "L1", "last_verified": "2026-01-10",
          "confidence": "A", "scope": "company-wide", "means": "lifetime repeat purchase"}
    l3 = {"term": "retention_rate", "layer": "L3", "last_verified": "2026-01-10",
          "confidence": "A", "scope": "area", "means": "90-day cohort return"}
    res = b1c.resolve_conflict(l1, l3)
    assert res["winner"] is l3            # the area contract wins
    assert res["winner_layer"] == "L3"
    assert res["decided_by"] == "source-authority"
    assert res["flagged_conflict"] is True
    # the load-bearing guarantee: never silently picks the company doc
    assert res["winner"] is not l1


def test_area_wins_even_when_company_has_higher_confidence():
    # source authority (rung 2) fires before confidence (rung 3): a high-confidence company term
    # still loses to a lower-confidence area contract
    l1 = {"layer": "L1", "last_verified": "2026-01-10", "confidence": "A"}
    l3 = {"layer": "L3", "last_verified": "2026-01-10", "confidence": "C"}
    res = b1c.resolve_conflict(l1, l3)
    assert res["winner"] is l3 and res["decided_by"] == "source-authority"
    assert res["flagged_conflict"] is True


def test_recency_decides_first_and_can_pick_either_side():
    # same authority layer: the first rung (recency) settles it, and it is not rigged to one side
    older = {"layer": "L3", "last_verified": "2026-01-01"}
    newer = {"layer": "L3", "last_verified": "2026-06-01"}
    res = b1c.resolve_conflict(older, newer)          # newer is the l3 arg
    assert res["winner"] is newer and res["decided_by"] == "recency"
    res2 = b1c.resolve_conflict(newer, older)         # newer is the l1 arg
    assert res2["winner"] is newer and res2["decided_by"] == "recency"


def test_confidence_then_specificity_break_remaining_ties():
    # recency ties (no dates) and authority ties (same layer): confidence decides
    a = {"layer": "L3", "confidence": "B", "scope": "area"}
    b = {"layer": "L3", "confidence": "A", "scope": "area"}
    res = b1c.resolve_conflict(a, b)
    assert res["winner"] is b and res["decided_by"] == "confidence"
    # confidence also ties: specificity decides (the more specific scope wins)
    broad = {"layer": "L3", "confidence": "A", "scope": "company-wide"}
    narrow = {"layer": "L3", "confidence": "A", "scope": "dataset"}
    res2 = b1c.resolve_conflict(broad, narrow)
    assert res2["winner"] is narrow and res2["decided_by"] == "specificity"


def test_unresolved_conflict_escalates_to_human_never_silent():
    # every rung ties: the resolver does not invent a winner, it flags for a human
    a = {"layer": "L3", "confidence": "A", "scope": "area"}
    b = {"layer": "L3", "confidence": "A", "scope": "area"}
    res = b1c.resolve_conflict(a, b)
    assert res["winner"] is None
    assert res["winner_layer"] is None
    assert res["decided_by"] == "human"
    assert res["flagged_conflict"] is True   # still surfaced loudly, never silently dropped


# ---- the real fixtures: the company glossary disagrees with the L3 contract -----------------

def test_real_l1_glossary_loses_to_l3_contract():
    glossary = [t for ov in b1c.build().read_overlays()
                for t in (ov or {}).get("glossary", []) if t["term"] == "retention_rate"][0]
    contract = [m for ov in b3.build().read_overlays()
                for m in (ov or {}).get("metrics", []) if m["metric"] == "retention_rate"][0]
    contract = {**contract, "term": contract["metric"]}
    # the two really do disagree on what "retention" means
    assert b1c.definitions_disagree(glossary, contract)
    res = b1c.resolve_conflict(glossary, contract)
    assert res["winner"] is contract          # the area L3 contract wins
    assert res["flagged_conflict"] is True
    assert res["decided_by"] in ("source-authority", "recency")


# ---- the spec is registered with an honest status ------------------------------------------

def test_setupspec_registered_buildable_now():
    spec = registry()["B1c-company-glossary"]
    assert spec.layer == "L1"
    assert spec.status == "buildable-now"
    assert spec.build is b1c.build


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b1c_company_glossary:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
