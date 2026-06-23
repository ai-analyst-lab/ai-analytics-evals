#!/usr/bin/env python3
"""Tests for the shared substrate: A1 reliability grader, A2 known-answer grader + the SQL-gold
helper, B-recall, and the B3 reference setup. Hermetic: A2 runs against a tiny in-memory DuckDB,
no analyst repo and no warehouse. Run: python3 tests/test_substrate.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders.a1_reliability import ReliabilityGrader
from aievals.graders.a2_known_answer import (
    KnownAnswerGrader, values_match, ancestor_diff, equivalence_judge,
)
from aievals.data.gold import GoldCase, schema_checksum
from aievals.harness import recall as rc
from aievals.setups import b3_metric_definition as b3
from aievals.harness.setups import compose_metrics

# Real measured first-run fixtures (same as the comparison tests).
NO_DEF = [
    {"headline": "84.8%", "definition_source": "my own choice"},
    {"headline": "75.2%", "definition_source": "my own choice"},
    {"headline": "84.8%", "definition_source": "my own choice"},
]
WITH_DEF = [{"headline": "55.4%", "definition_source": "metric dictionary"} for _ in range(3)]


def _duckdb_with_orders():
    import duckdb
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE orders (id INTEGER, customer INTEGER, status VARCHAR)")
    conn.execute("INSERT INTO orders VALUES (1,1,'completed'),(2,1,'completed'),"
                 "(3,2,'completed'),(4,3,'cancelled')")
    return conn


# ---- A1 reliability grader -----------------------------------------------------------------

def test_a1_flags_drift_and_passes_stable():
    g = ReliabilityGrader()
    drift = g.grade({"runs": NO_DEF})
    assert drift.kind == "flag" and drift.status == "flag" and drift.value is False
    stable = g.grade({"runs": WITH_DEF})
    assert stable.status == "pass" and stable.value is True
    # never a correctness score: it is a self-consistency flag, and says so
    assert "stability, not correctness" in stable.detail
    assert g.cost_tier == "exploratory"  # the cheapest read, runs at every intensity


def test_a1_handles_empty_and_unparseable():
    g = ReliabilityGrader()
    assert g.grade({"runs": []}).status == "not-applicable"
    assert g.grade({"runs": [{"headline": "n/a"}]}).status == "not-applicable"


# ---- A2 known-answer grader + gold helper --------------------------------------------------

def test_values_match_tolerant():
    assert values_match(55.4, 55.4)
    assert values_match(55.41, 55.4, rel_tol=0.005)
    assert not values_match(75.2, 55.4)
    assert not values_match(None, 55.4)


def test_a2_passes_correct_fails_wrong():
    conn = _duckdb_with_orders()
    # gold: number of completed orders = 3, computed in SQL at eval time (not hardcoded here)
    gold = GoldCase(question="how many completed orders",
                    sql="SELECT count(*) FROM orders WHERE status='completed'",
                    tables=("orders",))
    g = KnownAnswerGrader()
    ok = g.grade({"headline": "3"}, gold=gold, conn=conn)
    assert ok.status == "pass" and ok.value == 1.0
    bad = g.grade({"headline": "4"}, gold=gold, conn=conn)
    assert bad.status == "fail" and bad.value == 0.0


def test_a2_checksum_mismatch_flags_stale_gold_not_wrong_analyst():
    conn = _duckdb_with_orders()
    bound = schema_checksum(conn, ("orders",))
    gold = GoldCase(question="q", sql="SELECT count(*) FROM orders WHERE status='completed'",
                    tables=("orders",), schema_checksum="deadbeefdeadbeef")
    g = KnownAnswerGrader()
    res = g.grade({"headline": "3"}, gold=gold, conn=conn)
    assert res.status == "flag"  # the gold is stale, not the analyst wrong
    assert "stale gold" in res.detail
    # and a matching checksum lets the real grade through
    gold2 = GoldCase(question="q", sql=gold.sql, tables=("orders",), schema_checksum=bound)
    assert g.grade({"headline": "3"}, gold=gold2, conn=conn).status == "pass"


def test_a2_blocks_without_connection():
    gold = GoldCase(question="q", sql="SELECT 1", tables=())
    res = KnownAnswerGrader().grade({"headline": "1"}, gold=gold, conn=None)
    assert res.status == "blocked" and "connection" in res.blocked_on


def test_a2c_ancestor_diff_and_blocked_equivalence_judge():
    assert ancestor_diff("SELECT 1", "select   1 ;") == "identical"
    assert ancestor_diff("SELECT 1", "SELECT 2") == "changed"
    # the semantic equivalence judge is blocked on calibration, and says so rather than guessing
    ej = equivalence_judge("SELECT 1", "SELECT 2")
    assert ej["status"] == "blocked" and ej["verdict"] is None


# ---- B-recall ------------------------------------------------------------------------------

def test_recall_gates_on_citation():
    fired = rc.context_recall(WITH_DEF)
    assert fired["full_recall"] and rc.should_run_comparison(fired) is True
    missed = rc.context_recall(NO_DEF)
    assert missed["fired"] is False and rc.should_run_comparison(missed) is False
    partial = rc.context_recall(WITH_DEF[:2] + NO_DEF[:1])
    assert 0 < partial["recall"] < 1 and rc.should_run_comparison(partial) is False


# ---- B3 reference setup --------------------------------------------------------------------

def test_b3_setup_stages_the_canonical_contract():
    setup = b3.build()                      # defaults to our canonical fixture
    overlays = setup.read_overlays()
    metrics = compose_metrics([], overlays)
    names = [m["metric"] for m in metrics]
    assert "retention_rate" in names
    # meaning-only: the contract carries no result number anywhere
    blob = str(overlays)
    assert "55.4" not in blob and "%" not in blob
    assert b3.baseline().layer is None     # the no-definition baseline


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_substrate:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
