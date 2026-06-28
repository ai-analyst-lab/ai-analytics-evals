"""Side-by-side comparison of two eval run records (D22): the same suite under two engines.

The cell that matters is cost_per_correct — accuracy beside the dollars it took to get there. Also
surfaces where the two models disagree per case (which questions one got right and the other missed),
so the comparison is "where is the open model good enough," not just a single winner.
"""
from __future__ import annotations

import html
from pathlib import Path

from aievals.html_style import page

# (aggregate key, display name, formatter) — each formatter is applied to both runs' aggregate.
_METRICS = [
    ("accuracy", "Accuracy", lambda a: f"{(a.get('accuracy') or 0) * 100:.1f}%"),
    ("passed", "Passed / total", lambda a: f"{a.get('passed', '?')}/{a.get('total', '?')}"),
    ("avg_query_similarity", "Avg query-similarity", lambda a: f"{(a.get('avg_query_similarity') or 0):.2f}"),
    ("avg_latency_ms", "Avg latency (ms)", lambda a: f"{a.get('avg_latency_ms', '—')}"),
    ("total_cost", "Total cost ($)", lambda a: f"{a.get('total_cost', '—')}"),
    ("cost_per_correct", "Cost per correct ($)", lambda a: f"{a.get('cost_per_correct', '—')}"),
    ("total_tokens", "Total tokens", lambda a: f"{a.get('total_tokens', '—')}"),
]


def _label(run, fallback):
    return run.get("model") or fallback


def compare_runs(run_a, run_b):
    """Structured comparison: each run's aggregate, and per-case agreement/disagreement by question."""
    aa, ab = run_a.get("aggregate", {}) or {}, run_b.get("aggregate", {}) or {}
    by_q_a = {c["question"]: c for c in run_a.get("cases", [])}
    by_q_b = {c["question"]: c for c in run_b.get("cases", [])}
    questions = list(by_q_a) + [q for q in by_q_b if q not in by_q_a]
    cases = []
    for q in questions:
        ca, cb = by_q_a.get(q, {}), by_q_b.get(q, {})
        pa, pb = ca.get("passed"), cb.get("passed")
        cases.append({"question": q, "a_passed": pa, "b_passed": pb,
                      "a_value": ca.get("analyst_value"), "b_value": cb.get("analyst_value"),
                      "disagree": pa != pb})
    return {"aggregate_a": aa, "aggregate_b": ab, "cases": cases,
            "disagreements": sum(1 for c in cases if c["disagree"])}


def render_comparison(run_a, run_b, out_path, title="Model comparison", label_a="A", label_b="B"):
    """Write a self-contained side-by-side HTML comparing two run records. Returns the path."""
    la, lb = _label(run_a, label_a), _label(run_b, label_b)
    cmp = compare_runs(run_a, run_b)
    aa, ab = cmp["aggregate_a"], cmp["aggregate_b"]

    metric_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{html.escape(fmt(aa))}</td>"
        f"<td>{html.escape(fmt(ab))}</td></tr>"
        for _key, name, fmt in _METRICS)
    summary = (f"<table><thead><tr><th>metric</th><th>{html.escape(str(la))}</th>"
               f"<th>{html.escape(str(lb))}</th></tr></thead><tbody>{metric_rows}</tbody></table>")

    def mark(p):
        return "✓" if p else ("✗" if p is not None else "—")

    case_rows = "".join(
        f"<tr style=\"{'background:#fff7ed' if c['disagree'] else ''}\">"
        f"<td>{html.escape(str(c['question']))}</td>"
        f"<td>{mark(c['a_passed'])} <small>{html.escape(str(c['a_value']))}</small></td>"
        f"<td>{mark(c['b_passed'])} <small>{html.escape(str(c['b_value']))}</small></td></tr>"
        for c in cmp["cases"])
    cases_tbl = (f"<table><thead><tr><th>question</th><th>{html.escape(str(la))}</th>"
                 f"<th>{html.escape(str(lb))}</th></tr></thead><tbody>{case_rows}</tbody></table>")

    meta = (f"split: {html.escape(str(run_a.get('split', '')))} · "
            f"{cmp['disagreements']} of {len(cmp['cases'])} cases disagree · "
            f"context: {html.escape(str((run_a.get('context_state') or {}).get('n', '?')))} metrics defined")
    body = (f'<div class="card"><h3>{html.escape(str(la))} vs {html.escape(str(lb))}</h3>'
            f'<p>{meta}</p>{summary}</div>\n'
            f'<div class="card"><h3>Per-case (highlighted = disagreement)</h3>{cases_tbl}</div>')
    doc = page(title, "Same suite, two engines. Cost per correct is the cell that matters.", body)
    Path(out_path).write_text(doc)
    return out_path
