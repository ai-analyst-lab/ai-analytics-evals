"""The one HTML look every readout shares (the editorial-light palette).

monitor.py established the style: a light page, white cards with a thin border, amber as the one
accent, muted grays for labels. Rather than re-typing that CSS in every renderer (the monitor, the
error-cluster readout, the per-analysis scorecard), the palette and the page wrapper live here once
and everything imports them. One file to change the look, no drift between readouts.
"""
from __future__ import annotations

import html as _html

# The amber accent and the status colors, named so every readout reads the same.
AMBER = "#d97706"
GREEN = "#16a34a"
RED = "#dc2626"
GRAY = "#888"

# The base look, lifted verbatim from the monitor so the readouts are visibly one family.
BASE_CSS = """
 body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:32px;color:#1a1a1a;background:#fafafa}
 h1{font-size:20px;margin-bottom:2px} .sub{color:#888;font-size:13px;margin-bottom:18px}
 .card{background:#fff;border:1px solid #e5e5e5;border-radius:8px;padding:20px;margin:16px 0}
 h3{font-size:14px;color:#444;margin:0 0 12px}
 table{border-collapse:collapse;width:100%;font-size:14px}
 th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #eee}
 th{color:#666;font-weight:600} code{background:#f3f3f3;padding:1px 5px;border-radius:3px;font-size:12px}
"""

# Status word -> color. The vocabulary is wider than a grader's STATUSES on purpose: a readout is
# fed human-friendly words too (ok, green, warn, act, abstain), and they all map to the same palette.
_STATUS_COLOR = {
    "pass": GREEN, "ok": GREEN, "green": GREEN, "match": GREEN, "act": GREEN,
    "fail": RED, "red": RED, "abstain": RED, "miss": RED,
    "flag": AMBER, "warn": AMBER, "amber": AMBER, "yellow": AMBER, "investigate": AMBER,
    "blocked": GRAY, "not-applicable": GRAY, "n/a": GRAY, "gray": GRAY, "grey": GRAY,
}


def status_color(status):
    """The palette color for a status word (case-insensitive). Unknown words read gray, never
    crash, so a readout degrades to neutral rather than lying with a green."""
    return _STATUS_COLOR.get(str(status).strip().lower(), GRAY)


def esc(x):
    """HTML-escape any value (the renderers pass dicts, numbers, None through here)."""
    return _html.escape(str(x))


def page(title, sub, body, *, extra_css=""):
    """Wrap a body in the shared editorial-light page. `extra_css` lets one readout add its own
    rules (the cluster cards, the scorecard lanes) without forking the base look."""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">\n'
            f'<title>{esc(title)}</title>\n'
            f'<style>{BASE_CSS}{extra_css}</style></head><body>\n'
            f'<h1>{esc(title)}</h1>\n'
            f'<div class="sub">{sub}</div>\n'
            f'{body}\n'
            f'</body></html>')
