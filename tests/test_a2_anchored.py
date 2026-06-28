"""A2-known-answer on ANCHORED gold cases (value set, no SQL).

Regression: A2 used to call compute_gold(conn, gold.sql) unconditionally, so an anchored case
(verified value, empty sql) crashed. It must resolve to the anchored value instead, needing no
connection and no schema-checksum check.
"""
from aievals.graders import _load, base as gb
from aievals.data.gold import GoldCase


def _a2():
    _load.load_all()
    return gb.registry()["A2-known-answer"]()


ANCHORED = GoldCase(question="What is total completed revenue?", value=3150899.34, sql="",
                    snapshot_tag="2026-06-25", verified_by="shane")


def _status(r):
    return (r.as_dict() if hasattr(r, "as_dict") else r)["status"]


def test_a2_anchored_passes_matching_answer_without_conn():
    # no conn supplied: an anchored value needs no recompute, so it must not block or crash
    r = _a2().grade({"headline": 3150899.34}, gold=ANCHORED, conn=None)
    assert _status(r) == "pass"


def test_a2_anchored_fails_mismatched_answer_without_conn():
    r = _a2().grade({"headline": 5907972.60}, gold=ANCHORED, conn=None)
    assert _status(r) == "fail"


def test_a2_computed_still_blocks_without_conn():
    # a computed case (no anchored value) still requires a connection, unchanged behavior
    computed = GoldCase(question="trivial", sql="select 1", snapshot_tag="2026-06-25", verified_by="shane")
    r = _a2().grade({"headline": 1.0}, gold=computed, conn=None)
    assert _status(r) == "blocked"
