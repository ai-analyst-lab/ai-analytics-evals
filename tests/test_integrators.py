#!/usr/bin/env python3
"""Tests for the integrators that ride on the full registry: C1 scorecard, Track D pipeline map,
E1 campaign. Hermetic. Run: python3 tests/test_integrators.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders import _load, base as gb
from aievals.graders.a2_known_answer import KnownAnswerGrader
from aievals.graders.a3_provenance import ProvenanceGrader
from aievals.data.gold import GoldCase
from aievals import scorecard as sc
from aievals import pipeline as pl
from aievals import campaign as cp

_load.load_all()


def _duckdb_orders():
    import duckdb
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE orders (id INTEGER, status VARCHAR)")
    conn.execute("INSERT INTO orders VALUES (1,'completed'),(2,'completed'),(3,'completed')")
    return conn


GOOD_FOOTER = {"source": "orders table", "freshness": "2024-12-31", "confidence": "green"}


# ---- C1 scorecard --------------------------------------------------------------------------

def test_anti_gaming_garbage_number_perfect_footer_scores_low():
    """A wrong number with a perfect receipt must NOT score green: correctness dominates presence."""
    conn = _duckdb_orders()
    gold = GoldCase(question="how many completed orders",
                    sql="SELECT count(*) FROM orders WHERE status='completed'", tables=("orders",))
    output = {"headline": "999", "footer": GOOD_FOOTER}   # wrong number, immaculate footer
    card = sc.score_analysis("how many completed orders", output,
                             [KnownAnswerGrader, ProvenanceGrader],
                             intensity="decision-grade", gold=gold, conn=conn)
    pv = card.present_vs_correct()
    assert any(r.status == "pass" for r in pv["present"])   # the footer is well-formed
    assert any(r.status == "fail" for r in pv["correct"])   # the number is wrong
    assert card.verdict() == "fail"                          # and the card is not green


def test_correct_number_and_footer_passes():
    conn = _duckdb_orders()
    gold = GoldCase(question="q", sql="SELECT count(*) FROM orders WHERE status='completed'",
                    tables=("orders",))
    card = sc.score_analysis("q", {"headline": "3", "footer": GOOD_FOOTER},
                             [KnownAnswerGrader, ProvenanceGrader],
                             intensity="decision-grade", gold=gold, conn=conn)
    assert card.verdict() == "pass"


def test_propagation_gating_right_number_wrong_question():
    """A correct number computed for the wrong question does not score green."""
    conn = _duckdb_orders()
    gold = GoldCase(question="q", sql="SELECT count(*) FROM orders WHERE status='completed'",
                    tables=("orders",))
    card = sc.score_analysis("q", {"headline": "3", "footer": GOOD_FOOTER},
                             [KnownAnswerGrader, ProvenanceGrader],
                             intensity="decision-grade", propagation_ok=False, gold=gold, conn=conn)
    assert card.verdict() == "fail"


def test_intensity_dial_runs_fewer_checks_when_exploratory():
    allg = list(gb.registry().values())
    expl = sc.score_analysis("q", {"runs": [{"headline": "1%"}]}, allg, intensity="exploratory")
    audit = sc.score_analysis("q", {"runs": [{"headline": "1%"}]}, allg, intensity="audit-grade")
    assert len(expl.results) == 1                 # one check at exploratory
    assert len(audit.results) == len(allg)        # the full set at audit-grade
    assert len(expl.results) < len(audit.results)


def test_no_cross_regime_number():
    """The card's verdict is a label, never a summed number, and results keep distinct bases."""
    conn = _duckdb_orders()
    gold = GoldCase(question="q", sql="SELECT count(*) FROM orders WHERE status='completed'",
                    tables=("orders",))
    card = sc.score_analysis("q", {"headline": "3", "footer": GOOD_FOOTER},
                             [KnownAnswerGrader, ProvenanceGrader],
                             intensity="decision-grade", gold=gold, conn=conn)
    assert isinstance(card.verdict(), str)
    bases = set(card.by_truth_basis())
    assert "computable" in bases and "presence" in bases   # different kinds of truth, kept apart
    assert card.producer_is_grader is False                # producer is not grader, recorded


# ---- Track D pipeline map ------------------------------------------------------------------

def test_six_pieces_map_to_real_graders_and_setups():
    from aievals.setups import load_all as sload, base as sb
    _load.load_all(); sload()
    graders = set(gb.registry())
    setups = set(sb.registry())
    assert len(pl.PIECES) == 6
    for p in pl.PIECES:
        assert p.detect, f"piece {p.n} has no detect checks"
        for gname in p.detect:
            assert gname in graders, f"piece {p.n} names unknown grader {gname}"
        for skey in p.supply:
            assert skey in setups, f"piece {p.n} names unknown setup {skey}"


def test_per_tier_counts_and_endpoints():
    assert pl.checks_for(3, "exploratory") == 1
    assert pl.checks_for(6, "audit-grade") >= pl.checks_for(6, "exploratory")
    assert pl.endpoints_pull_most() is True       # pieces 1 and 6 pull the most setups
    assert pl.piece(3).proven is True             # only the metric-definition loop is proven today
    assert pl.piece(1).proven is False


# ---- E1 campaign ---------------------------------------------------------------------------

def test_rank_marks_sub_noise_not_distinguishable():
    floor = 0.02
    ranked = cp.rank_methods(
        [{"setup": "B3", "delta": 0.40}, {"setup": "B4", "delta": 0.001}, {"setup": "B7", "delta": 0.10}],
        floor)
    assert ranked[0]["setup"] == "B3" and ranked[0]["distinguishable"] is True
    sub = [r for r in ranked if r["setup"] == "B4"][0]
    assert sub["distinguishable"] is False and "noise" in sub["verdict"]


def test_granularity_not_resolved_without_all_arms():
    res = cp.resolve_granularity([{"setup": "per-metric", "delta": 0.3}], floor=0.02)
    assert res["resolved"] is False and "per-metric" not in (res["winner"] or "")
    full = cp.resolve_granularity(
        [{"setup": "per-metric", "delta": 0.30}, {"setup": "single-index", "delta": 0.05},
         {"setup": "domain-bundled", "delta": 0.01}], floor=0.02)
    assert full["resolved"] is True and full["winner"] == "per-metric"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_integrators:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
