"""Run the held-out gold suite against a batch of analyst results and render the readout.

Given a gold YAML (the hidden suite) and a list of per-case analyst results, this grades each
case on TWO signals, reusing the existing graders, and never recomputes a value from a literal:

  ACCURACY          values_match(analyst_value, resolve_gold(conn, case)) -> pass/fail. The gold
                    is recomputed in SQL at eval time (resolve_gold), so it cannot rot. Accuracy is
                    the SUITE metric: pass count / total.

  QUERY-SIMILARITY  the analyst's SQL vs the case's approved (blessed) query. Two parts:
                      - ancestor_diff: 'identical' or 'changed' (the always-correct text check)
                      - a 0..1 token-overlap similarity (Jaccard over normalized SQL tokens), so a
                        changed-but-close query still earns partial credit and the suite can report
                        an average closeness without claiming semantic equivalence.

Precision/recall/F1 are deliberately NOT computed here: those are for judge calibration, out of
scope. The suite metric is accuracy.

The connection is always supplied by the caller (a DuckDB path or a DBAPI/Snowflake connection);
this module embeds no credential and no data. Gold values are never shown in the readout.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from aievals.data.gold import load_gold_cases, resolve_gold
from aievals.graders.a2_known_answer import values_match, ancestor_diff
from aievals.stats.reliability import parse_number


def _normalize_sql(sql):
    """Whitespace- and case-normalize SQL (mirror of the grader's normalizer) before tokenizing."""
    s = re.sub(r"\s+", " ", (sql or "").strip().lower())
    return s.rstrip(";").strip()


def token_overlap_similarity(a, b):
    """0..1 token-overlap (Jaccard) similarity between two SQL strings. 1.0 == same token set,
    0.0 == disjoint. A cheap, deterministic closeness signal: it does NOT claim two queries are
    semantically equivalent (that judge is blocked on calibration), only how much text they share."""
    ta = set(re.findall(r"\w+", _normalize_sql(a)))
    tb = set(re.findall(r"\w+", _normalize_sql(b)))
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def grade_case(case, analyst_value, analyst_query, conn):
    """Grade one case on both signals. Returns a per-case record (no gold leaked beyond this dict;
    the caller decides whether to show the gold, and the HTML readout does not)."""
    gold_value = resolve_gold(conn, case)
    # Warehouses return numeric scalars as Decimal/int; coerce to float so the comparison math
    # (values_match does float arithmetic) never trips on a Decimal-minus-float TypeError.
    if gold_value is not None:
        gold_value = float(gold_value)
    a_value = parse_number(analyst_value)
    tol = getattr(case, "rel_tol", None)
    passed = values_match(a_value, gold_value, rel_tol=tol) if tol else values_match(a_value, gold_value)
    # Unit-aware: a rate reported as a percent (33.24) vs a fraction gold (0.3324) is the SAME number,
    # just a different reporting unit. Pass it, but flag it so the readout shows it was a unit difference,
    # not a clean match. Only kicks in when the gold is a rate (0 < gold <= 1) and analyst is ~100x.
    unit_adjusted = False
    if not passed and a_value is not None and gold_value is not None and 0 < abs(gold_value) <= 1.0:
        if values_match(a_value / 100.0, gold_value, rel_tol=(tol or 0.005)):
            passed = True
            unit_adjusted = True

    diff = ancestor_diff(analyst_query or "", case.approved_query or case.sql or "")
    similarity = token_overlap_similarity(analyst_query or "", case.approved_query or case.sql or "")

    return {
        "question": case.question,
        "difficulty": case.difficulty,
        "type": case.type,
        "gold_value": gold_value,
        "analyst_value": a_value,
        "passed": bool(passed),
        "unit_adjusted": unit_adjusted,
        "analyst_query": analyst_query or "",
        "query_diff": diff,                      # 'identical' | 'changed'
        "query_similarity": round(similarity, 4),
    }


def _match_results(cases, per_case_results):
    """Pair each analyst result to its gold case by question text. Returns (pairs, unmatched)."""
    by_q = {c.question.strip().lower(): c for c in cases}
    pairs, unmatched = [], []
    for r in per_case_results:
        c = by_q.get(str(r.get("question", "")).strip().lower())
        (pairs.append((c, r)) if c is not None else unmatched.append(r.get("question")))
    return pairs, unmatched


def aggregate(per_case):
    """Suite aggregates: accuracy = pass count / total; avg query-similarity over graded cases.

    Cost, latency, and tokens are summed when the per-case records carry them (the live driver
    attaches tokens/cost/latency_ms per case, D4); on a hand-graded batch they are absent and simply
    omitted. cost_per_correct is the dollars-per-correct-answer cell the model comparison turns on
    (D22)."""
    total = len(per_case)
    passed = sum(1 for p in per_case if p["passed"])
    sims = [p["query_similarity"] for p in per_case]
    agg = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "avg_query_similarity": round(sum(sims) / len(sims), 4) if sims else 0.0,
    }
    costs = [p["cost"] for p in per_case if p.get("cost") is not None]
    lats = [p["latency_ms"] for p in per_case if p.get("latency_ms") is not None]
    toks = [p["tokens"] for p in per_case if p.get("tokens") is not None]
    if costs:
        agg["total_cost"] = round(sum(costs), 6)
        agg["cost_per_correct"] = round(sum(costs) / passed, 6) if passed else None
    if lats:
        agg["total_latency_ms"] = int(sum(lats))
        agg["avg_latency_ms"] = int(sum(lats) / len(lats))
    if toks:
        agg["total_tokens"] = int(sum(toks))
    return agg


def render_html(results, out_path, title="Held-out gold eval"):
    """Render the per-case results table + aggregate headline, reusing monitor.py's card style.
    Shows gold next to analyst so a human can audit; this readout stays with the harness."""
    agg = results["aggregate"]
    rows = []
    for p in results["cases"]:
        ok = p["passed"]
        badge = (f'<span style="color:#16a34a;font-weight:700">PASS</span>' if ok
                 else '<span style="color:#dc2626;font-weight:700">FAIL</span>')
        sim = p["query_similarity"]
        sim_color = "#16a34a" if sim >= 0.85 else "#d97706" if sim >= 0.5 else "#dc2626"
        rows.append(
            f"<tr><td>{html.escape(str(p['question']))}"
            f"<div class='meta'>{html.escape(str(p.get('difficulty') or ''))}"
            f" &middot; {html.escape(str(p.get('type') or ''))}</div></td>"
            f"<td class='num'>{html.escape(str(p['gold_value']))}</td>"
            f"<td class='num'>{html.escape(str(p['analyst_value']))}</td>"
            f"<td>{badge}</td>"
            f"<td class='num' style='color:{sim_color};font-weight:600'>{sim:.2f}"
            f"<div class='meta'>{html.escape(str(p['query_diff']))}</div></td></tr>")
    table = ("<table><thead><tr><th>question</th><th>gold</th><th>analyst</th>"
             "<th>result</th><th>query sim</th></tr></thead><tbody>"
             + "".join(rows) + "</tbody></table>")

    acc_pct = int(round(agg["accuracy"] * 100))
    acc_color = "#16a34a" if agg["accuracy"] >= 0.8 else "#d97706" if agg["accuracy"] >= 0.5 else "#dc2626"
    headline = (
        f"<div class='kpis'>"
        f"<div class='kpi'><div class='big' style='color:{acc_color}'>{acc_pct}%</div>"
        f"<div class='lbl'>accuracy &mdash; {agg['passed']}/{agg['total']} cases</div></div>"
        f"<div class='kpi'><div class='big' style='color:#d97706'>{agg['avg_query_similarity']:.2f}</div>"
        f"<div class='lbl'>avg query similarity</div></div></div>")

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:32px;color:#1a1a1a;background:#fafafa}}
 h1{{font-size:20px;margin-bottom:2px}} .sub{{color:#888;font-size:13px;margin-bottom:18px}}
 .card{{background:#fff;border:1px solid #e5e5e5;border-radius:8px;padding:20px;margin:16px 0}}
 h3{{font-size:14px;color:#444;margin:0 0 12px}}
 .kpis{{display:flex;gap:40px}} .kpi .big{{font-size:40px;font-weight:800;line-height:1}}
 .kpi .lbl{{color:#777;font-size:13px;margin-top:4px}}
 table{{border-collapse:collapse;width:100%;font-size:14px}}
 th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #eee;vertical-align:top}}
 th{{color:#666;font-weight:600}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
 .meta{{color:#999;font-size:11px;margin-top:2px}}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="sub">Run {html.escape(str(results.get('run_id','')))} &middot; {html.escape(str(results.get('timestamp','')))}.
 Accuracy is the suite metric (pass/total). Gold is recomputed in SQL at eval time, never hardcoded.</div>
<div class="card">{headline}</div>
<div class="card"><h3>Per-case results</h3>{table}</div>
</body></html>"""
    Path(out_path).write_text(doc)
    return out_path


def run_eval(cases_path, per_case_results, conn, out_dir, run_id=None, title="Held-out gold eval", split=None, meta=None):
    """Grade a batch of analyst results against the hidden gold suite and write the readout.

    cases_path:        path to the gold YAML (the hidden suite).
    per_case_results:  list of {question, analyst_value, analyst_query}; the live driver also
                       attaches per-case {latency_ms, tokens, cost, model} (D4), carried through.
    conn:              connection used to recompute each gold in SQL (DuckDB or DBAPI/Snowflake).
    out_dir:           where the JSON + HTML readout are written.
    split:             "train" | "test" | None (D8). Grades only that split's cases; None grades all.
                       Recorded in the run JSON so a train run and a test run are never confused.
    meta:              optional run provenance merged into the record without clobbering core keys
                       (git_sha, model, context_state, changelog, ...) so the run is self-describing
                       (D4) and the monitor can read git_sha/changelog directly (BL-C1).

    Returns a results dict {run_id, timestamp, split, aggregate, cases, unmatched, json_path, html_path}.
    """
    cases = load_gold_cases(cases_path, split=split)
    pairs, unmatched = _match_results(cases, per_case_results)

    by_q = {}
    for r in per_case_results:
        by_q[str(r.get("question", "")).strip().lower()] = r
    per_case = []
    for case, r in pairs:
        gc = grade_case(case, r.get("analyst_value"), r.get("analyst_query"), conn)
        # Carry through the live driver's per-case capture (D4): cost, latency, tokens, and which
        # model produced the answer. Present on a live run, absent on a hand-graded batch.
        for k in ("latency_ms", "tokens", "cost", "model"):
            if r.get(k) is not None:
                gc[k] = r[k]
        per_case.append(gc)

    # Error analysis: cluster the failures into ranked modes so the readout names the dominant bug
    # (the V6 hinge). Diagnosis — what each mode means and what to fix — stays the student's job.
    gold_by_q = {c.question.strip().lower(): c for c in cases}
    failed = []
    for p in per_case:
        if not p["passed"]:
            gc = gold_by_q.get(str(p["question"]).strip().lower())
            failed.append({
                "question": p["question"], "gold_value": p["gold_value"],
                "analyst_value": p["analyst_value"], "query": p.get("analyst_query", ""),
                "approved_query": (gc.approved_query or gc.sql) if gc else "",
                "definition": ((gc.note or "") if gc else ""),
            })
    clusters = {}
    if failed:
        try:
            from aievals.cluster_errors import cluster_failures
            clusters = cluster_failures(failed)
        except Exception:
            clusters = {}

    run_id = run_id or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    results = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "split": split,
        "aggregate": aggregate(per_case),
        "failure_modes": [{"mode": m, "count": len(cs)} for m, cs in clusters.items()],
        "cases": per_case,
        "unmatched": unmatched,
    }
    # Merge run provenance (git_sha, model, context_state, ...) without clobbering core keys, so the
    # record is self-describing and the monitor reads git_sha/changelog straight off it (D4, BL-C1).
    for k, v in (meta or {}).items():
        results.setdefault(k, v)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{run_id}.json"
    json_path.write_text(json.dumps(results, indent=2, default=str))
    html_path = render_html(results, out / f"{run_id}.html", title=title)

    results["json_path"] = str(json_path)
    results["html_path"] = str(html_path)
    if clusters:
        try:
            from aievals.cluster_errors import render_clusters_html
            results["clusters_path"] = str(
                render_clusters_html(clusters, out / f"{run_id}-clusters.html"))
        except Exception:
            pass
    return results
