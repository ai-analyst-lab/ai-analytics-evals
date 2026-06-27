"""Render one analysis's scorecard as HTML (the V5 confidence read).

This is the per-analysis card a builder looks at before they act on a number. It keeps the lanes
apart by source and never sums them into one score, because they are different kinds of truth: a
query-match similarity, a self-consistency spread, a provenance receipt, and the query checks each
answer a different question, and rolling them into one number would let a clean receipt paper over a
wrong answer. The card shows the four lanes side by side with their own status, puts the overall
confidence read (act / investigate / abstain) up top where the decision is made, and lists what to
fix. The confidence read is a judgment over the lanes, not an average of them.

Input shape (a plain dict, so this renders a card from any source without importing the grader stack):
    {
      "question": "...",
      "lanes": {
        "query_match":  {"status": "...", "similarity": 0.9, "approved_query_ref": "gold-12"},
        "consistency":  {"status": "...", "spread": "..."},
        "provenance":   {"status": "...", "fields": [...]},
        "query_checks": {"status": "...", "issues": [...]},
      },
      "confidence": "act" | "investigate" | "abstain",
      "what_to_fix": ["...", ...],
    }

Reuses the monitor's editorial-light palette via aievals.html_style; it does not re-type the look.
"""
from __future__ import annotations

from pathlib import Path

from aievals.html_style import page, esc, status_color, GREEN, AMBER, RED, GRAY

# The four lanes, in display order, with the label and the per-lane fields worth showing. Kept apart
# on purpose: each lane has its own source of truth and is never added to the others.
LANES = (
    ("query_match", "Query match", ("similarity", "approved_query_ref")),
    ("consistency", "Self-consistency", ("spread",)),
    ("provenance", "Provenance", ("fields",)),
    ("query_checks", "Query checks", ("issues",)),
)

# The confidence read, prominent: what to do, and the color it reads in.
_CONFIDENCE = {
    "act": (GREEN, "Act", "The lanes agree; the number is safe to act on."),
    "investigate": (AMBER, "Investigate", "A lane raised a flag; look before you act."),
    "abstain": (RED, "Abstain", "A lane failed; do not act on this number yet."),
}

_SCORECARD_CSS = """
 .read{display:flex;align-items:center;gap:14px;padding:16px 20px;border-radius:8px;color:#fff;margin:16px 0}
 .read .verb{font-size:22px;font-weight:700;letter-spacing:.5px}
 .read .why{font-size:14px;opacity:.95}
 .lanes{display:flex;gap:16px;flex-wrap:wrap}
 .lane{flex:1;min-width:200px;background:#fff;border:1px solid #e5e5e5;border-radius:8px;padding:16px}
 .lane h4{margin:0 0 4px;font-size:13px;color:#444}
 .badge{display:inline-block;color:#fff;border-radius:10px;padding:1px 9px;font-size:12px;font-weight:600}
 .lane dl{margin:10px 0 0;font-size:12px;color:#555}
 .lane dt{color:#999;margin-top:6px} .lane dd{margin:0 0 0 0}
 .fix{margin:6px 0 0;padding-left:18px} .fix li{font-size:14px;color:#333;padding:2px 0}
 .nosum{color:#888;font-size:12px;margin-top:6px;font-style:italic}
"""


def _fmt_value(v):
    if isinstance(v, (list, tuple)):
        return ", ".join(esc(x) for x in v) if v else "(none)"
    if isinstance(v, float):
        return f"{v:.3f}"
    return esc(v)


def _lane_card(key, label, fields, lane):
    status = lane.get("status", "n/a")
    rows = []
    for f in fields:
        if f in lane and lane[f] is not None:
            rows.append(f"<dt>{esc(f)}</dt><dd>{_fmt_value(lane[f])}</dd>")
    # surface any extra keys the caller put on the lane that we did not name explicitly
    for k, v in lane.items():
        if k not in ("status",) and k not in fields and v is not None:
            rows.append(f"<dt>{esc(k)}</dt><dd>{_fmt_value(v)}</dd>")
    dl = f"<dl>{''.join(rows)}</dl>" if rows else ""
    return (f'<div class="lane"><h4>{esc(label)}</h4>'
            f'<span class="badge" style="background:{status_color(status)}">{esc(status)}</span>'
            f'{dl}</div>')


def render_scorecard_html(scorecard, out_path, title="Analysis scorecard"):
    """Render one analysis's scorecard as an HTML card. The four lanes sit side by side with their
    own status, the confidence read is prominent, and 'what to fix' is a list. The lanes are never
    summed into a single number. `scorecard` is the dict documented at the top. Returns out_path."""
    lanes = scorecard.get("lanes", {})
    lane_html = "".join(
        _lane_card(key, label, fields, lanes.get(key, {})) for key, label, fields in LANES)

    conf_key = str(scorecard.get("confidence", "investigate")).lower()
    color, verb, why = _CONFIDENCE.get(conf_key, (GRAY, esc(conf_key), ""))
    read = (f'<div class="read" style="background:{color}">'
            f'<span class="verb">{esc(verb)}</span>'
            f'<span class="why">{esc(why)}</span></div>')

    fixes = scorecard.get("what_to_fix") or []
    if fixes:
        fix_html = ('<div class="card"><h3>What to fix</h3>'
                    f'<ul class="fix">{"".join(f"<li>{esc(x)}</li>" for x in fixes)}</ul></div>')
    else:
        fix_html = '<div class="card"><h3>What to fix</h3><p class="nosum">Nothing flagged.</p></div>'

    body = (
        f"{read}\n"
        f'<div class="card"><h3>Question</h3><p>{esc(scorecard.get("question", ""))}</p></div>\n'
        f'<div class="card"><h3>Lanes (kept apart, never summed)</h3>'
        f'<div class="lanes">{lane_html}</div>'
        f'<p class="nosum">Four sources of truth, four columns. They are not added into one score.</p>'
        f'</div>\n'
        f"{fix_html}")

    sub = "One analysis, read four ways. The confidence read is a judgment over the lanes, not their average."
    doc = page(title, sub, body, extra_css=_SCORECARD_CSS)
    Path(out_path).write_text(doc)
    return out_path
