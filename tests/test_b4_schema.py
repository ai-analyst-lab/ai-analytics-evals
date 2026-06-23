#!/usr/bin/env python3
"""Tests for the B4 schema-and-quirks setup (canonical layer L4).

Hermetic: the with-schema arm reads a temp YAML overlay (no warehouse, no analyst repo), and the
off arm stages nothing, so toggling the layer is visible as the difference between the two arms.
Also checks the canonical fixture default works and that the overlay is structure-and-quirks with
no result number in it. Run: python3 tests/test_b4_schema.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.setups import b4_schema as b4
from aievals.setups.base import registry


def _temp_schema(d):
    """Write a tiny schema-and-quirks overlay into directory d and return d."""
    (Path(d) / "schema.yaml").write_text(
        "tables:\n"
        "  - table: orders\n"
        "    keys: [order_id, customer_id]\n"
        "joins:\n"
        "  - from: orders.customer_id\n"
        "    to: customers.customer_id\n"
        "quirks:\n"
        "  - cancelled orders keep their row, so filter status='completed'\n"
    )
    return d


# ---- the toggle: with-schema composes the overlay, off does not ----------------------------

def test_toggle_stages_different_content():
    with tempfile.TemporaryDirectory() as d:
        _temp_schema(d)
        on = b4.build(schema_dir=d)
        off = b4.baseline()

        on_facts = b4.compose_schema(on.read_overlays())
        off_facts = b4.compose_schema(off.read_overlays())

        # the with-schema arm carries L4 structure and quirks
        assert [t["table"] for t in on_facts["tables"]] == ["orders"]
        assert len(on_facts["joins"]) == 1
        assert len(on_facts["quirks"]) == 1
        # the off arm stages nothing: every section is empty
        assert off_facts == {"tables": [], "joins": [], "quirks": []}
        # so toggling the layer changes the staged content
        assert on_facts != off_facts


def test_arm_layers_are_honest():
    with tempfile.TemporaryDirectory() as d:
        _temp_schema(d)
        on = b4.build(schema_dir=d)
        assert on.layer == "L4" and on.reader == "file"
        assert b4.baseline().layer is None   # the bare baseline touches no layer


# ---- the canonical fixture default ---------------------------------------------------------

def test_default_reads_canonical_fixture():
    setup = b4.build()                        # no schema_dir: use our teaching fixture
    facts = b4.compose_schema(setup.read_overlays())
    tables = [t["table"] for t in facts["tables"]]
    assert "orders" in tables and "customers" in tables
    assert facts["joins"] and facts["quirks"]
    # structure and warnings, never an answer: no result number, no percent sign anywhere
    blob = str(setup.read_overlays())
    assert "%" not in blob
    assert not any(ch.isdigit() for ch in blob)


# ---- the honest status carried in code -----------------------------------------------------

def test_registers_buildable_now():
    spec = registry()["B4-schema"]
    assert spec.status == "buildable-now"     # pure staging, runnable today
    assert spec.blocked_on is None
    assert spec.layer == "L4"
    assert "C-store.md" in spec.source
    assert spec.build is b4.build


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b4_schema:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
