#!/usr/bin/env python3
"""Tests for the A8 execution grader: tests-as-truth for analysis code, graded as a partial,
multi-assertion DataFrame match. Hermetic: builds tiny pandas DataFrames in memory, no warehouse,
no analyst repo, no model in the loop, and no exec of any code string. The known-answer DataFrames
are built here, not read from a result module, so no result number is hardcoded into the grader.
Run: python3 tests/test_a8_execution.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders.a8_execution import ExecutionGrader, partial_match


def _expected_rates():
    """A small known-answer table: per-region checkout conversion. region is the key column,
    conversions/sessions/rate are value columns compared with tolerance."""
    return pd.DataFrame({
        "region": ["north", "south", "east"],
        "conversions": [50, 30, 20],
        "sessions": [200, 150, 100],
        "rate": [0.25, 0.20, 0.20],
    })


def _expected_weeks():
    """A windowed table: weeks W1..W4. week (a string) is the key, so an off-by-one window shows up
    as a missing key, not a numeric drift."""
    return pd.DataFrame({
        "week": ["W1", "W2", "W3", "W4"],
        "active": [100, 120, 140, 160],
    })


# ---- partial_match: the new mechanism -----------------------------------------------------------

def test_partial_match_exact_passes():
    exp = _expected_rates()
    m = partial_match(exp.copy(), exp)
    assert m["ok"] is True and m["failures"] == []


def test_partial_match_tolerates_extra_columns_and_rows_and_order():
    exp = _expected_rates()
    actual = exp.copy()
    actual["note"] = ["a", "b", "c"]                       # extra column, allowed
    extra = pd.DataFrame({"region": ["west"], "conversions": [5],
                          "sessions": [50], "rate": [0.10], "note": ["d"]})
    actual = pd.concat([actual.iloc[::-1], extra], ignore_index=True)  # reorder + extra row
    m = partial_match(actual, exp)
    assert m["ok"] is True, m["failures"]


def test_partial_match_tolerant_numeric_compare():
    exp = _expected_rates()
    actual = exp.copy()
    actual.loc[0, "rate"] = 0.2500004                      # within default rel_tol
    assert partial_match(actual, exp)["ok"] is True


def test_partial_match_columns_subset_restriction():
    exp = _expected_rates()
    actual = exp[["region", "rate"]].copy()                # missing conversions/sessions
    # full check fails on the missing columns
    assert partial_match(actual, exp)["ok"] is False
    # restricting to the columns the actual carries passes
    assert partial_match(actual, exp, columns=["region", "rate"])["ok"] is True


# ---- the grader: correct code passes -----------------------------------------------------------

def test_a8_correct_dataframe_passes_all_assertions():
    g = ExecutionGrader()
    exp = _expected_rates()
    res = g.grade({"result_df": exp.copy()}, expected_df=exp)
    assert res.kind == "score" and res.status == "pass" and res.value == 1.0
    assert res.family == "execution" and res.truth_basis == "execution"


# ---- wrong denominator: a numeric cell beyond tolerance ----------------------------------------

def test_a8_wrong_denominator_fails_the_numeric_assertion():
    g = ExecutionGrader()
    exp = _expected_rates()
    wrong = exp.copy()
    # analyst divided by the wrong denominator: rate for north computed as 50/100 = 0.50, not 0.25
    wrong.loc[0, "rate"] = 0.50
    res = g.grade({"result_df": wrong}, expected_df=exp)
    assert res.status == "fail" and res.value == 0.0
    # the SPECIFIC assertion is named: the rate column on the north row
    assert "tolerant numeric compare" in res.detail
    assert "'rate'" in res.detail and "north" in res.detail


# ---- off-by-one window: one wrong row ----------------------------------------------------------

def test_a8_off_by_one_window_fails_the_row_assertion():
    g = ExecutionGrader()
    exp = _expected_weeks()
    # analyst used weeks W2..W5 instead of W1..W4: W1 is missing (off-by-one window)
    shifted = pd.DataFrame({"week": ["W2", "W3", "W4", "W5"], "active": [120, 140, 160, 180]})
    res = g.grade({"result_df": shifted}, expected_df=exp)
    assert res.status == "fail" and res.value == 0.0
    # the SPECIFIC assertion is named: the missing W1 row
    assert "row subset" in res.detail and "W1" in res.detail


# ---- missing column ----------------------------------------------------------------------------

def test_a8_missing_column_fails_the_column_assertion():
    g = ExecutionGrader()
    exp = _expected_rates()
    dropped = exp.drop(columns=["rate"])
    res = g.grade({"result_df": dropped}, expected_df=exp)
    assert res.status == "fail" and res.value == 0.0
    assert "column subset" in res.detail and "rate" in res.detail


# ---- honest labels: blocked and not-applicable, never a silent pass ----------------------------

def test_a8_blocks_without_a_result_df():
    g = ExecutionGrader()
    exp = _expected_rates()
    res = g.grade({}, expected_df=exp)
    assert res.status == "blocked" and res.value is None
    assert res.blocked_on and "result_df" in res.blocked_on


def test_a8_blocks_on_non_dataframe_input():
    g = ExecutionGrader()
    exp = _expected_rates()
    res = g.grade({"result_df": [1, 2, 3]}, expected_df=exp)
    assert res.status == "blocked" and res.value is None
    assert "DataFrame" in res.blocked_on


def test_a8_not_applicable_without_a_known_answer():
    g = ExecutionGrader()
    res = g.grade({"result_df": _expected_rates()})  # no expected_df
    assert res.status == "not-applicable" and res.value is None


def test_a8_score_is_single_regime_never_additive():
    # A8 yields one score in the execution regime; it never sums across regimes.
    g = ExecutionGrader()
    exp = _expected_rates()
    res = g.grade({"result_df": exp.copy()}, expected_df=exp)
    assert res.kind == "score" and res.surface == "code"
    assert g.cost_tier == "decision-grade"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_a8_execution:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
