#!/usr/bin/env python3
"""Tests for aievals/verify_gold.py — candidate verification against a fake connection.

Hermetic: a FakeConn returns a pinned value per SQL (or None, or raises). Proves verify_cases reports
ok for a real number, FAIL+reason for NULL, and FAIL+error for a broken query — without a warehouse.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.verify_gold import verify_cases, format_report

CANDIDATES = """cases:
  - question: "good scalar"
    sql: "select 1"
    approved_query: "select 1"
    tables: [orders]
    difficulty: easy
    type: "single-table aggregate"
    split: train
  - question: "returns null"
    sql: "select null_query"
    approved_query: "select null_query"
    tables: [orders]
    difficulty: medium
    type: "ratio"
    split: test
  - question: "broken sql"
    sql: "select boom"
    approved_query: "select boom"
    tables: [orders]
    difficulty: hard
    type: "multi-step"
    split: train
"""


class _Cur:
    def __init__(self, v): self._v = v
    def fetchone(self): return (self._v,)
    def fetchall(self): return [(self._v,)]


class FakeConn:
    def __init__(self, vals): self.vals = vals
    def execute(self, sql):
        k = sql.strip()
        if k not in self.vals:
            raise KeyError(f"no value for: {sql}")
        return _Cur(self.vals[k])


def test_verify_reports_ok_null_and_error():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "cand.yaml"; p.write_text(CANDIDATES)
        conn = FakeConn({"select 1": 42, "select null_query": None})  # "select boom" absent -> error
        results = verify_cases(p, conn)
        by_q = {r["question"]: r for r in results}
        assert by_q["good scalar"]["ok"] is True and by_q["good scalar"]["value"] == 42.0
        assert by_q["returns null"]["ok"] is False and by_q["returns null"]["error"] == "returned NULL"
        assert by_q["broken sql"]["ok"] is False and "no value for" in by_q["broken sql"]["error"]
        assert by_q["good scalar"]["split"] == "train"


def test_verify_split_filter_and_report():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "cand.yaml"; p.write_text(CANDIDATES)
        conn = FakeConn({"select 1": 42, "select null_query": None})
        train = verify_cases(p, conn, split="train")
        assert len(train) == 2 and all(r["split"] == "train" for r in train)
        report = format_report(verify_cases(p, conn))
        assert "verified 1/3" in report and "OK" in report and "FAIL" in report
