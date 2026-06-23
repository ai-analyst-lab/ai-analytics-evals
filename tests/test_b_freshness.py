#!/usr/bin/env python3
"""Tests for B-freshness: the schema-diff guard, the inject-a-change demo, and the staged-context
setup. Hermetic: the real checksums are computed against a tiny in-memory DuckDB, no warehouse and
no analyst repo. Run: python3 tests/test_b_freshness.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.data.gold import schema_checksum
from aievals.harness.setups import Setup, compose_metrics
from aievals.setups import b_freshness as bf


def _orders_conn():
    import duckdb
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE orders (id INTEGER, customer INTEGER, net_revenue DECIMAL)")
    return conn


# ---- the guard: detect_stale ---------------------------------------------------------------

def test_detect_stale_catches_change_and_passes_fresh():
    # differing checksums = the context was built against a schema that has since changed
    assert bf.detect_stale("aaaa1111", "bbbb2222") is True
    # identical checksums = fresh, safe to load
    assert bf.detect_stale("aaaa1111", "aaaa1111") is False


def test_detect_stale_on_real_checksums():
    conn = _orders_conn()
    bound = schema_checksum(conn, ("orders",))            # checksum at context-build time
    # identical schema -> fresh
    assert bf.detect_stale(bound, schema_checksum(conn, ("orders",))) is False
    # inject a realistic breaking change (the C-lifecycle net_revenue -> net_rev_v2 rename)
    conn.execute("ALTER TABLE orders RENAME COLUMN net_revenue TO net_rev_v2")
    live = schema_checksum(conn, ("orders",))
    assert live != bound
    assert bf.detect_stale(bound, live) is True           # caught
    conn.close()


# ---- the guard wrapper and the demo --------------------------------------------------------

def test_guard_quarantines_stale_and_loads_fresh():
    conn = _orders_conn()
    bound = schema_checksum(conn, ("orders",))
    fresh = bf.guard(conn, ("orders",), context_checksum=bound)
    assert fresh["stale"] is False and fresh["action"] == "load"
    conn.execute("ALTER TABLE orders RENAME COLUMN net_revenue TO net_rev_v2")
    stale = bf.guard(conn, ("orders",), context_checksum=bound)
    assert stale["stale"] is True and stale["action"] == "quarantine"
    assert stale["context_checksum"] != stale["live_checksum"]
    conn.close()


def test_demo_self_contained_catches_injected_change():
    # no connection passed: the demo builds its own in-memory schema, injects the rename, guards
    result = bf.demo_schema_change()
    assert result["stale"] is True and result["action"] == "quarantine"
    assert result["context_checksum"] != result["live_checksum"]
    # a real (computable) checksum, not a literal answer baked into the module
    assert isinstance(result["live_checksum"], str) and len(result["live_checksum"]) > 0


# ---- the staged-context setup --------------------------------------------------------------

def test_build_returns_two_runnable_arms():
    arms = bf.build()                                      # defaults to the canonical fixture
    assert isinstance(arms, list) and len(arms) == 2
    names = {a.name for a in arms}
    assert names == {"fresh-context", "stale-context"}
    for arm in arms:
        assert isinstance(arm, Setup) and arm.layer == "L4"
        overlays = arm.read_overlays()
        metrics = compose_metrics([], overlays)
        # the worked content is the meaning-only retention contract, carrying no result number
        assert any(m["metric"] == "retention_rate" for m in metrics)
        blob = str(overlays)
        assert "55.4" not in blob and "%" not in blob


# ---- honest status -------------------------------------------------------------------------

def test_spec_is_registered_partial_with_frontier_named():
    from aievals.setups.base import registry
    spec = registry()["B-freshness"]
    assert spec.layer == "L4"
    # the honest label: the demo + guard are buildable, the full lifecycle is frontier
    assert spec.status == "partial"
    assert spec.source == "C-lifecycle.md"
    assert spec.blocked_on and "frontier" in spec.blocked_on
    # the partial spec still produces runnable arms now
    assert callable(spec.build) and len(spec.build()) == 2


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b_freshness:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
