"""Render the eval monitor as a self-contained HTML dashboard (the V7 monitor).

Tracks the system's accuracy on the held-out eval suite over time: a line chart per run, a run table with
the delta and a degradation/improvement flag, and the changelog (what changed between runs). One HTML file,
no external dependencies, open it or share it. The gold answers are never shown here; they stay hidden with
the harness.
"""
from __future__ import annotations

import html
from pathlib import Path

from aievals.html_style import page


def _run_view(r):
    """Flatten a run record into the fields the dashboard needs, reading accuracy/passed/total from
    `aggregate` (the run_eval shape) or the top level (a hand-built dict), and tolerating a missing
    git_sha/changelog so a run logged before those existed still renders (BL-C1)."""
    a = r.get("aggregate") or {}
    acc = a.get("accuracy", r.get("accuracy"))
    return {
        "run_id": r.get("run_id", "?"),
        "timestamp": r.get("timestamp", ""),
        "git_sha": r.get("git_sha", ""),
        "changelog": r.get("changelog", ""),
        "split": r.get("split", a.get("split", "")),
        "accuracy": acc if acc is not None else 0.0,
        "passed": a.get("passed", r.get("passed", "?")),
        "total": a.get("total", r.get("total", "?")),
    }


def render_dashboard(runs, out_path, title="Eval monitor"):
    """runs: list of run records (the run_eval shape, with an `aggregate` block), oldest first.
    Writes a self-contained HTML dashboard to out_path and returns the path."""
    runs = [_run_view(r) for r in runs]
    W, H, pad = 660, 240, 40
    n = max(1, len(runs) - 1)
    xs = [pad + (W - 2 * pad) * i / n for i in range(len(runs))]
    ys = [H - pad - (H - 2 * pad) * r["accuracy"] for r in runs]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#d97706"/>'
                   f'<text x="{x:.1f}" y="{y-10:.1f}" font-size="11" fill="#555" text-anchor="middle">'
                   f'{int(r["accuracy"]*100)}%</text>'
                   for x, y, r in zip(xs, ys, runs))
    grid = "".join(
        f'<line x1="{pad}" y1="{H-pad-(H-2*pad)*v:.1f}" x2="{W-pad}" y2="{H-pad-(H-2*pad)*v:.1f}" stroke="#eee"/>'
        f'<text x="6" y="{H-pad-(H-2*pad)*v+4:.1f}" font-size="11" fill="#999">{int(v*100)}</text>'
        for v in (0, 0.25, 0.5, 0.75, 1.0))
    chart = (f'<svg width="{W}" height="{H}" role="img">{grid}'
             f'<polyline points="{pts}" fill="none" stroke="#d97706" stroke-width="2"/>{dots}</svg>')

    rows, prev = [], None
    for r in runs:
        acc = r["accuracy"]
        if prev is None:
            delta, flag, color = "-", "baseline", "#888"
        else:
            d = acc - prev
            delta = f"{d*100:+.0f} pts"
            flag, color = (("improved", "#16a34a") if d > 0 else
                           ("DEGRADED", "#dc2626") if d < 0 else ("flat", "#888"))
        rows.append(
            f"<tr><td>{html.escape(str(r['run_id']))}</td>"
            f"<td>{html.escape(str(r.get('timestamp', '')))}</td>"
            f"<td><code>{html.escape(str(r['git_sha']))}</code></td>"
            f"<td>{html.escape(str(r['split']))}</td>"
            f"<td><b>{int(acc*100)}%</b> ({r['passed']}/{r['total']})</td>"
            f"<td style='color:{color};font-weight:600'>{delta} {flag}</td>"
            f"<td>{html.escape(str(r.get('changelog', '')))}</td></tr>")
        prev = acc
    table = ("<table><thead><tr><th>run</th><th>when</th><th>sha</th><th>split</th><th>accuracy</th>"
             "<th>vs prev</th><th>changelog</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")

    body = (f'<div class="card"><h3>Accuracy over time</h3>{chart}</div>\n'
            f'<div class="card"><h3>Runs</h3>{table}</div>')
    doc = page(title,
               "Accuracy on the held-out eval suite over time. Gold answers are hidden from the analyst.",
               body)
    Path(out_path).write_text(doc)
    return out_path
