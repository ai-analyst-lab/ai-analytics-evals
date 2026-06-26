"""Render the eval monitor as a self-contained HTML dashboard (the V7 monitor).

Tracks the system's accuracy on the held-out eval suite over time: a line chart per run, a run table with
the delta and a degradation/improvement flag, and the changelog (what changed between runs). One HTML file,
no external dependencies, open it or share it. The gold answers are never shown here; they stay hidden with
the harness.
"""
from __future__ import annotations

import html
from pathlib import Path


def render_dashboard(runs, out_path, title="Eval monitor"):
    """runs: list of run records, oldest first, each a dict:
        {run_id, timestamp, git_sha, accuracy (0..1), passed, total, changelog}
    Writes a self-contained HTML dashboard to out_path and returns the path."""
    runs = list(runs)
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
            f"<td><code>{html.escape(str(r.get('git_sha', '')))}</code></td>"
            f"<td><b>{int(acc*100)}%</b> ({r.get('passed', '?')}/{r.get('total', '?')})</td>"
            f"<td style='color:{color};font-weight:600'>{delta} {flag}</td>"
            f"<td>{html.escape(str(r.get('changelog', '')))}</td></tr>")
        prev = acc
    table = ("<table><thead><tr><th>run</th><th>when</th><th>sha</th><th>accuracy</th>"
             "<th>vs prev</th><th>changelog</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:32px;color:#1a1a1a;background:#fafafa}}
 h1{{font-size:20px;margin-bottom:2px}} .sub{{color:#888;font-size:13px;margin-bottom:18px}}
 .card{{background:#fff;border:1px solid #e5e5e5;border-radius:8px;padding:20px;margin:16px 0}}
 h3{{font-size:14px;color:#444;margin:0 0 12px}}
 table{{border-collapse:collapse;width:100%;font-size:14px}}
 th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #eee}}
 th{{color:#666;font-weight:600}} code{{background:#f3f3f3;padding:1px 5px;border-radius:3px;font-size:12px}}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="sub">Accuracy on the held-out eval suite over time. Gold answers are hidden from the analyst.</div>
<div class="card"><h3>Accuracy over time</h3>{chart}</div>
<div class="card"><h3>Runs</h3>{table}</div>
</body></html>"""
    Path(out_path).write_text(doc)
    return out_path
