"""Verify candidate gold cases by recomputing each case's sql against a live connection.

Gold discipline: a case is not trusted until its sql actually RUNS and returns a real number. This
runs each candidate's sql (via compute_gold) and reports the value or the error, so candidates can be
confirmed (and any broken sql fixed) before they are merged into the trusted suite. No credentials or
network here — the caller supplies the connection (the analyst side holds the warehouse creds)."""
from __future__ import annotations

from aievals.data.gold import load_gold_cases, compute_gold


def verify_cases(cases_path, conn, split=None):
    """Run each candidate's sql and report a list of
    {question, difficulty, type, split, value, ok, error}. Writes nothing; trusts nothing."""
    cases = load_gold_cases(cases_path, split=split)
    results = []
    for c in cases:
        rec = {"question": c.question, "difficulty": c.difficulty, "type": c.type,
               "split": c.split, "value": None, "ok": False, "error": None}
        try:
            v = compute_gold(conn, c.sql)
            if v is None:
                rec["error"] = "returned NULL"
            else:
                rec["value"] = float(v)
                rec["ok"] = True
        except Exception as e:  # a broken sql is a finding, not a crash
            rec["error"] = str(e)
        results.append(rec)
    return results


def format_report(results):
    """A scannable text report of verify_cases output."""
    ok = sum(1 for r in results if r["ok"])
    lines = [f"verified {ok}/{len(results)} candidates returned a real number", ""]
    for r in results:
        status = "OK  " if r["ok"] else "FAIL"
        val = r["value"] if r["ok"] else r["error"]
        lines.append(f"[{status}] {str(r['split']):5} {str(r['difficulty']):6} {r['question']}")
        lines.append(f"          -> {val}")
    return "\n".join(lines)
