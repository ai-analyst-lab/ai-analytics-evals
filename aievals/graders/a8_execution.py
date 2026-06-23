"""A8 Execution (family: execution).

Where correct-looking analysis code computes the wrong thing: an off-by-one window, a double
count, the wrong denominator. The arithmetic runs cleanly, the meaning is wrong. The known-answer
move for code is tests-as-truth: run the analysis against a verifiable case and compare what it
produced to what it should have produced, with no model in the loop. The truth basis is execution,
not a judge.

This grader checks the analyst's analysis RESULT (the pandas DataFrame the analyst-side code
produced), not by executing untrusted code strings inside the tool (we never exec analyst code
here, that is a sandbox concern that lives outside this grader), but by comparing the produced
DataFrame to a known-answer expected DataFrame. The comparison is a MULTI-ASSERTION, PARTIAL match,
because a correct analysis can legitimately carry extra columns or extra rows and can phrase a
float a hair differently. The three assertions, in order, are:

  1. Column subset: every required column is present in the produced DataFrame (extra columns are
     fine, that is the "partial" in partial match).
  2. Row subset: every expected row appears in the produced DataFrame, matched on its key (the
     non-numeric) columns rather than by position, so row order does not matter and an extra row
     in the actual is tolerated.
  3. Tolerant numeric compare: each numeric cell of a matched row agrees within a relative
     tolerance, so 0.5540001 and 0.554 are the same answer but a wrong denominator is not.

The new mechanism here is partial_match(), which names the SPECIFIC assertion that failed (a
missing column, a missing row, or a particular numeric cell that drifted past tolerance) instead
of returning a bare pass/fail. That specificity is the whole point: "column 'rate' expected 0.55
got 0.33" is actionable in a way that "DataFrames differ" is not.

The grader returns a kind="score" result (1.0 when every assertion passes, 0.0 otherwise) and a
detail that names what broke. It holds no gold and no path: the expected DataFrame is the
known-answer case, supplied by the caller (computed in SQL at eval time by the A2 gold machinery,
never a hardcoded literal in this module).
"""
import pandas as pd

from aievals.graders.base import Grader, register
from aievals.graders.a2_known_answer import values_match, DEFAULT_REL_TOL


def _numeric_columns(expected_df, cols):
    """The value columns (tolerant compare) versus the key columns (exact match). A column is a
    value column when its expected dtype is numeric; everything else (strings, dates, booleans)
    is a key used to line an expected row up with the row that should carry it."""
    numeric = [c for c in cols if pd.api.types.is_numeric_dtype(expected_df[c])]
    keys = [c for c in cols if c not in numeric]
    return numeric, keys


def partial_match(actual_df, expected_df, columns=None, rel_tol=DEFAULT_REL_TOL):
    """Multi-assertion, partial DataFrame match. Returns {"ok": bool, "failures": [str, ...]} where
    each failure names the specific assertion that caught the problem.

    Partial means: the actual DataFrame may carry extra columns and extra rows. What it must do is
    contain, for every required column and every expected row, a matching cell (exact for key
    columns, within rel_tol for numeric columns). `columns` restricts the comparison to a subset of
    the expected columns; when None, every expected column is required.
    """
    failures = []
    cols = list(columns) if columns is not None else list(expected_df.columns)

    # Assertion 1: column subset. A missing required column is fatal, so report and stop here
    # (there is nothing to row-match against once a column the answer depends on is gone).
    missing_in_actual = [c for c in cols if c not in actual_df.columns]
    if missing_in_actual:
        failures.append(
            f"column subset: required column(s) {missing_in_actual} missing from actual "
            f"(actual has {list(actual_df.columns)})")
        return {"ok": False, "failures": failures}
    missing_in_expected = [c for c in cols if c not in expected_df.columns]
    if missing_in_expected:
        failures.append(
            f"column subset: expected_df has no column(s) {missing_in_expected}; "
            "cannot build a known answer for them")
        return {"ok": False, "failures": failures}

    numeric_cols, key_cols = _numeric_columns(expected_df, cols)
    actual = actual_df[cols].reset_index(drop=True)

    # Assertions 2 and 3: every expected row must be present (row subset), and its numeric cells
    # must agree within tolerance (tolerant numeric compare).
    for idx, exp_row in expected_df[cols].reset_index(drop=True).iterrows():
        if key_cols:
            mask = pd.Series(True, index=actual.index)
            for c in key_cols:
                mask &= (actual[c] == exp_row[c])
            candidates = actual[mask]
        else:
            candidates = actual

        key_repr = {c: exp_row[c] for c in key_cols} if key_cols else f"row {idx}"

        if len(candidates) == 0:
            failures.append(
                f"row subset: expected row {key_repr} has no matching row in actual "
                "(key columns do not line up)")
            continue

        # A candidate matches when every numeric cell agrees within tolerance. Pass on the first
        # full match; otherwise remember the nearest near-miss so we can name the offending cell.
        matched = False
        near_miss = None
        for _, cand in candidates.iterrows():
            offending = None
            for c in numeric_cols:
                if not values_match(float(cand[c]), float(exp_row[c]), rel_tol):
                    offending = (c, exp_row[c], cand[c])
                    break
            if offending is None:
                matched = True
                break
            if near_miss is None:
                near_miss = offending
        if not matched:
            c, expected_val, actual_val = near_miss
            failures.append(
                f"tolerant numeric compare: row {key_repr}, column {c!r} expected {expected_val} "
                f"got {actual_val} (beyond rel_tol {rel_tol})")

    return {"ok": len(failures) == 0, "failures": failures}


@register
class ExecutionGrader(Grader):
    name = "A8-execution"
    family = "execution"
    truth_basis = "execution"
    surface = "code"
    cost_tier = "decision-grade"

    def grade(self, output, *, intensity="decision-grade", run_type="table",
              expected_df=None, columns=None, rel_tol=DEFAULT_REL_TOL, **ctx):
        """`output` carries the analyst's produced DataFrame as output["result_df"]. `expected_df`
        is the known-answer DataFrame (computed by the gold machinery, not hardcoded). Returns a
        score: 1.0 when every assertion passes, 0.0 with the failing assertion named in detail."""
        if expected_df is None:
            return self.result(kind="score", status="not-applicable", value=None,
                               detail="no known-answer case (expected_df) for this analysis")

        result_df = output.get("result_df") if isinstance(output, dict) else output
        if result_df is None:
            return self.result(
                kind="score", status="blocked", value=None,
                blocked_on="no result_df in output",
                detail="A8 grades the analyst-produced DataFrame; none was supplied to grade")
        if not isinstance(result_df, pd.DataFrame) or not isinstance(expected_df, pd.DataFrame):
            return self.result(
                kind="score", status="blocked", value=None,
                blocked_on="result_df and expected_df must both be pandas DataFrames",
                detail="A8 compares DataFrames by execution; a non-DataFrame cannot be graded")

        match = partial_match(result_df, expected_df, columns=columns, rel_tol=rel_tol)
        checked = list(columns) if columns is not None else list(expected_df.columns)
        if match["ok"]:
            return self.result(
                kind="score", status="pass", value=1.0,
                detail=(f"all assertions passed: {len(checked)} column(s), "
                        f"{len(expected_df)} expected row(s), rel_tol {rel_tol}"))
        return self.result(
            kind="score", status="fail", value=0.0,
            detail="; ".join(match["failures"]))
