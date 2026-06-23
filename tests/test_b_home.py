#!/usr/bin/env python3
"""Tests for B-home: where a layer's context LIVES, with format held constant.

Hermetic: an in-memory DuckDB stands in for the warehouse home. We insert the SAME contract text
the repo fixture carries into a table row, then assert the WarehouseReader reads the SAME contract
MEANING as the repo FileReader (the home changed, the content did not), and that the NotionReader
reports blocked rather than silently returning empty. No analyst repo, no warehouse, no network.
Run: python3 tests/test_b_home.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.setups import b_home
from aievals.setups.base import registry, STATUSES
from aievals.harness.setups import compose_metrics, get_reader


def _duckdb_seeded_with_contract():
    """An in-memory DuckDB acting as the warehouse home, seeded with the contract TEXT in a row.
    The text is the exact bytes of the repo fixture, so 'same content, different home' is real."""
    import duckdb
    text = b_home.CONTRACT_FILE.read_text()
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE metric_contracts (metric VARCHAR, contract_text VARCHAR)")
    conn.execute("INSERT INTO metric_contracts VALUES (?, ?)", ["retention_rate", text])
    return conn


# ---- the home variable is isolated: same content, different home --------------------------------

def test_warehouse_home_reads_same_contract_as_repo_home():
    conn = _duckdb_seeded_with_contract()
    repo_overlays = b_home.repo_home().read_overlays()
    wh_overlays = b_home.warehouse_home(conn=conn).read_overlays()
    # Home changed, content identical: the parsed overlays are equal byte-for-byte in meaning.
    assert wh_overlays == repo_overlays
    # And both compose to the same retention metric by meaning, no result number anywhere.
    repo_metrics = compose_metrics([], repo_overlays)
    wh_metrics = compose_metrics([], wh_overlays)
    assert [m["metric"] for m in wh_metrics] == [m["metric"] for m in repo_metrics]
    assert "retention_rate" in [m["metric"] for m in wh_metrics]


def test_warehouse_reader_is_credential_free_and_takes_a_supplied_connection():
    # The reader holds no connection of its own; it reads only the one passed in via the spec.
    conn = _duckdb_seeded_with_contract()
    reader = get_reader("warehouse")
    overlays = reader.read({"conn": conn, "table": "metric_contracts"})
    assert overlays and overlays[0]["metrics"][0]["metric"] == "retention_rate"
    # No supplied connection means the analyst-side home is not wired: raise, do not return empty.
    raised = False
    try:
        reader.read({"conn": None, "table": "metric_contracts"})
    except RuntimeError as e:
        raised = True
        assert "no connection supplied" in str(e)
    assert raised


def test_warehouse_unseeded_table_raises_not_silently_empty():
    import duckdb
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE metric_contracts (metric VARCHAR, contract_text VARCHAR)")
    raised = False
    try:
        b_home.warehouse_home(conn=conn).read_overlays()
    except RuntimeError as e:
        raised = True
        assert "not seeded" in str(e)
    assert raised  # an empty table is not an empty-but-valid overlay


# ---- the blocked home reports blocked -----------------------------------------------------------

def test_notion_home_reports_blocked_not_empty():
    setup = b_home.notion_home()
    raised = False
    try:
        setup.read_overlays()
    except RuntimeError as e:
        raised = True
        assert "blocked" in str(e).lower() and "token" in str(e).lower()
    assert raised  # never silently returns [] for a blocked home


# ---- the unit's build and honest status ---------------------------------------------------------

def test_build_returns_all_homes_with_held_constant_content():
    setups = b_home.build()
    names = [s.name for s in setups]
    assert names == ["home-repo", "home-snowflake", "home-notion"]
    # Format held constant: every arm carries the SAME L3 contract layer, only the home varies.
    assert all(s.layer == "L3" for s in setups)
    readers = [s.reader for s in setups]
    assert readers == ["file", "warehouse", "notion"]


def test_spec_status_is_partial_and_honest():
    spec = registry()["B-home"]
    assert spec.status == "partial" and spec.status in STATUSES
    assert spec.layer is None  # cross-cutting axis, not a single layer
    assert "Snowflake" in spec.blocked_on and "Notion" in spec.blocked_on
    assert "Rule B" in spec.source


def test_no_hardcoded_result_number_anywhere():
    # The contract is meaning-only: no result figure lives in the module or the fixture it reads.
    src = (ROOT / "aievals" / "setups" / "b_home.py").read_text()
    fixture = b_home.CONTRACT_FILE.read_text()
    for blob in (src, fixture):
        assert "55.4" not in blob and "84.8" not in blob and "75.2" not in blob
    assert "%" not in fixture  # the meaning-only contract carries no percentage answer


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b_home:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
