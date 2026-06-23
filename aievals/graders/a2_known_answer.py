"""A2 Known-answer (family: computable).

Compare the analyst's number to a gold answer computed in SQL at eval time, never a literal.
The gold is bound to a snapshot tag and a schema checksum, so a real answer drift is told apart
from the data or schema changing underneath: a checksum mismatch invalidates the gold (re-derive
it) rather than failing the analyst for a number that moved because the table changed.

This module also carries the known-answer integrity infra the plan attaches to A2:
  - snapshot and checksum binding (W1.2): bound on the GoldCase, checked here.
  - A2c regression and ancestor-diff (Piece 2): diff a new query against a previously validated
    ancestor for the same question, and judge different-but-correct SQL as equivalent. Exact
    normalized-string equivalence is buildable now; the kappa-calibrated equivalence JUDGE for
    semantically-equal-but-textually-different SQL is BLOCKED on a labeled set (the same gate as
    A5), and says so rather than guessing.

The grader compares values; it holds no data and no path. The connection that recomputes the
gold is supplied by the caller (a DuckDB path for local practice data, or the analyst's
warehouse connection).
"""
import re

from aievals.graders.base import Grader, register
from aievals.stats.reliability import parse_number
from aievals.data.gold import compute_gold, schema_checksum

# Default relative tolerance for a numeric match (a fraction of the gold value).
DEFAULT_REL_TOL = 0.005


def values_match(analyst_value, gold_value, rel_tol=DEFAULT_REL_TOL):
    """Tolerant numeric compare: equal within rel_tol of the gold, with an exact-zero guard."""
    if analyst_value is None or gold_value is None:
        return False
    if gold_value == 0:
        return abs(analyst_value) <= rel_tol
    return abs(analyst_value - gold_value) / abs(gold_value) <= rel_tol


def _normalize_sql(sql):
    """Whitespace- and case-normalize SQL for an exact-equivalence check. This is the cheap,
    always-correct half of A2c; it only declares two queries equal when they are the same query
    written differently in spacing or case, never that two different queries mean the same."""
    s = re.sub(r"\s+", " ", sql.strip().lower())
    s = s.rstrip(";").strip()
    return s


def ancestor_diff(new_sql, ancestor_sql):
    """Diff a new query against a previously validated ancestor. Returns one of:
      'identical'         normalized text matches (safe to carry the ancestor's validation)
      'changed'          the text differs; whether it is still correct needs the equivalence
                         judge, which is blocked on calibration (see equivalence_judge)."""
    return "identical" if _normalize_sql(new_sql) == _normalize_sql(ancestor_sql) else "changed"


def equivalence_judge(new_sql, ancestor_sql):
    """The kappa-calibrated judge for different-but-correct SQL. BLOCKED: it needs a labeled set
    to calibrate before any 'these two different queries are equivalent' verdict can be trusted.
    Returns a blocked marker instead of a guess, so a changed query is never silently passed."""
    return {
        "status": "blocked",
        "blocked_on": "W4.1 labeled SQL-equivalence set (kappa calibration); same gate as A5",
        "verdict": None,
    }


@register
class KnownAnswerGrader(Grader):
    name = "A2-known-answer"
    family = "computable"
    truth_basis = "computable"
    surface = "number"
    cost_tier = "operational"

    def grade(self, output, *, intensity="decision-grade", run_type="single-number",
              gold=None, conn=None, rel_tol=DEFAULT_REL_TOL, ancestor_sql=None, **ctx):
        """`output` carries the analyst's number (output["headline"] or output["number"]) and,
        for A2c, its SQL (output["sql"]). `gold` is a GoldCase; `conn` recomputes it in SQL."""
        if gold is None:
            return self.result(kind="score", status="not-applicable", value=None,
                               detail="no gold case for this question")
        if conn is None:
            return self.result(kind="score", status="blocked", value=None,
                               blocked_on="no connection supplied to recompute the gold in SQL",
                               detail="A2 recomputes the gold at eval time; it needs a connection")

        # Snapshot/checksum binding (W1.2): a schema change invalidates the gold, not the analyst.
        if gold.schema_checksum and gold.tables:
            live = schema_checksum(conn, gold.tables)
            if live != gold.schema_checksum:
                return self.result(
                    kind="flag", status="flag", value=None,
                    detail=(f"stale gold: schema checksum {live} != bound {gold.schema_checksum}. "
                            "Re-derive the gold; this is not a wrong analyst."))

        gold_value = compute_gold(conn, gold.sql)
        analyst_value = parse_number(output.get("headline") or output.get("number")) \
            if isinstance(output, dict) else parse_number(output)

        match = values_match(analyst_value, gold_value, rel_tol)
        detail = (f"analyst {analyst_value} vs gold {gold_value} "
                  f"(computed in SQL, snapshot {gold.snapshot_tag}, rel_tol {rel_tol})")

        # A2c: if an ancestor query is supplied, fold its diff into the detail. A changed query
        # cannot be auto-passed on text alone; the equivalence judge is blocked, stated honestly.
        if ancestor_sql is not None and isinstance(output, dict) and output.get("sql"):
            diff = ancestor_diff(output["sql"], ancestor_sql)
            if diff == "identical":
                detail += "; A2c: query identical to validated ancestor"
            else:
                ej = equivalence_judge(output["sql"], ancestor_sql)
                detail += f"; A2c: query changed from ancestor, equivalence judge {ej['status']} ({ej['blocked_on']})"

        return self.result(
            kind="score",
            status="pass" if match else "fail",
            value=1.0 if match else 0.0,
            detail=detail,
        )
