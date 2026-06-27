"""Cluster failed eval cases into ranked error modes (the failure-triage readout).

When a run regresses you get a pile of FAILED cases. Staring at them one by one is slow; what you
want is "these 9 failures are all the same fan-out bug, fix that one thing." This module does the
grouping: a cheap rule-based first pass that reads the SQL and the value gap and names the mode, a
clustering step that ranks the modes by how many cases they own, an agent-assist hook for the modes
the heuristics miss, and an HTML readout in the shared editorial-light look.

A failed case is a dict:
    {question, gold_value, analyst_value, query, approved_query, definition}
and may optionally carry an `agent_label` (see classify_failure) and a `trace` (the action log the
agent reads). The heuristics are deliberately conservative: when no signature fires the mode is
"other", never a confident guess.

We reuse the A2 known-answer machinery instead of re-deriving it: `values_match` for "is the number
actually off", `ancestor_diff` for "is this query the same as the blessed one", and `_normalize_sql`
for the token comparison. The HTML reuses the monitor's palette via aievals.html_style.
"""
from __future__ import annotations

import re
from pathlib import Path

from aievals.graders.a2_known_answer import values_match, ancestor_diff, _normalize_sql
from aievals.html_style import AMBER, page, esc

# The error modes, in the order a card lists them when sizes tie. The first five are nameable bugs;
# "other" is the honest fallback for a failure no signature explains.
ERROR_MODES = (
    "undefined-metric-drift",   # definitional question, value far from gold, query unlike the blessed one
    "fan-out",                  # joined order_items and SUM'd an order-level column (rows multiplied)
    "wrong-filter",             # dropped status='completed', or counted cancelled/returned rows
    "wrong-grain",              # counted at the wrong grain (missing DISTINCT, or grouped differently)
    "wrong-source",             # read the wrong object (e.g. sessions.had_purchase instead of events)
    "other",
)

# Columns that live at the order grain; SUM'ing one of these across an order_items join double-counts.
_ORDER_LEVEL_COLS = ("total_amount", "order_total", "order_value", "order_amount", "revenue", "amount")

# How far off a value has to be (fraction of gold) before it counts as "far" for metric drift.
_FAR_REL = 0.10
# How dissimilar the analyst SQL has to be from the blessed SQL to read as "structurally different".
_STRUCT_SIM = 0.6


def _q(case, key):
    return (case.get(key) or "")


def _low(s):
    return _normalize_sql(s) if s else ""


def _has_completed_filter(sql):
    """True if the SQL filters orders to completed (the gold's filter)."""
    s = _low(sql)
    return bool(re.search(r"status\s*=\s*'completed'", s) or
                re.search(r"status\s+in\s*\([^)]*'completed'", s))


def _mentions_excluded_states(sql):
    """True if the SQL pulls in cancelled/returned rows that the gold excludes."""
    s = _low(sql)
    return bool(re.search(r"'(cancelled|canceled|returned|refunded)'", s))


def _sums_order_level_col(sql):
    s = _low(sql)
    cols = "|".join(_ORDER_LEVEL_COLS)
    return bool(re.search(rf"sum\s*\(\s*(?:[a-z_]+\.)?({cols})\b", s))


def _joins_order_items(sql):
    s = _low(sql)
    return "order_items" in s


def value_gap(case):
    """Relative gap between the analyst's number and the gold, or None if either is missing."""
    g, a = case.get("gold_value"), case.get("analyst_value")
    if g is None or a is None:
        return None
    if g == 0:
        return abs(a)
    return abs(a - g) / abs(g)


def value_is_far(case, rel=_FAR_REL):
    """The number is meaningfully off (beyond `rel` of gold). Uses A2's values_match for the
    'differs at all' read, then the gap for 'differs a lot'."""
    g, a = case.get("gold_value"), case.get("analyst_value")
    if g is None or a is None:
        return False
    if values_match(a, g):
        return False
    gap = value_gap(case)
    return gap is not None and gap > rel


def sql_similarity(a, b):
    """Token Jaccard over the two normalized queries, in [0,1]. 1.0 = same tokens, 0.0 = disjoint.
    Built on A2's _normalize_sql so the comparison matches the ancestor-diff normalization."""
    ta, tb = set(_normalize_sql(a).split()), set(_normalize_sql(b).split())
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def is_definitional(case):
    """True when the question is a definitional one whose metric is not pinned down: an empty or
    'undefined' definition, or a question that asks what a fuzzy metric means. These are the cases
    where two correct-looking analyses legitimately disagree because the metric was never defined."""
    d = (case.get("definition") or "").strip().lower()
    if d in ("", "none", "undefined", "n/a", "tbd"):
        return True
    q = (case.get("question") or "").lower()
    return bool(re.search(r"\b(retention|active user|active users|churn|engaged|power user|"
                          r"how do we define|what counts as|define)\b", q))


def structurally_different(case):
    """The analyst's query is not the blessed query AND shares few tokens with it."""
    q, aq = _q(case, "query"), _q(case, "approved_query")
    if not q or not aq:
        return False
    if ancestor_diff(q, aq) == "identical":
        return False
    return sql_similarity(q, aq) < _STRUCT_SIM


def classify_error(case):
    """Rule-based first pass: read the SQL text and the value gap, return one of ERROR_MODES.

    Order matters. The concrete SQL signatures (fan-out, wrong-source, wrong-filter, wrong-grain)
    are checked before the softer definitional-drift read, so a clear mechanical bug is named as
    that bug even when the question also happens to be definitional. Nothing matches -> "other"."""
    q = _q(case, "query")

    # fan-out: joined the line-item table and SUM'd a column that lives at the order grain.
    if _joins_order_items(q) and _sums_order_level_col(q):
        return "fan-out"

    # wrong-source: read a different object than the blessed query (the had_purchase/events swap).
    if _is_wrong_source(case):
        return "wrong-source"

    # wrong-filter: dropped the completed filter the gold uses, or counted cancelled/returned rows.
    if _is_wrong_filter(case):
        return "wrong-filter"

    # wrong-grain: counted at a different grain than blessed (DISTINCT mismatch or different GROUP BY).
    if _is_wrong_grain(case):
        return "wrong-grain"

    # undefined-metric-drift: a definitional question, the number is far off, and the query is built
    # differently from the blessed one. The metric was never pinned, so the analyst drifted.
    if is_definitional(case) and value_is_far(case) and structurally_different(case):
        return "undefined-metric-drift"

    return "other"


def _is_wrong_source(case):
    q, aq = _low(_q(case, "query")), _low(_q(case, "approved_query"))
    if not q:
        return False
    # the concrete swap the spec names: counting purchases off a session flag instead of events
    if "had_purchase" in q:
        return True
    # general object swap: blessed reads `events`, analyst reads `sessions` and never `events`
    if "events" in aq and "events" not in q and "sessions" in q:
        return True
    return False


def _is_wrong_filter(case):
    q, aq = _q(case, "query"), _q(case, "approved_query")
    if not q or not aq:
        return False
    # blessed filters to completed; analyst did not
    if _has_completed_filter(aq) and not _has_completed_filter(q):
        return True
    # analyst pulls cancelled/returned where the blessed query filters to completed
    if _has_completed_filter(aq) and _mentions_excluded_states(q):
        return True
    return False


def _group_by_cols(sql):
    m = re.search(r"group\s+by\s+(.+?)(?:order\s+by|having|limit|$)", _low(sql))
    if not m:
        return set()
    return {c.strip() for c in m.group(1).split(",") if c.strip()}


def _is_wrong_grain(case):
    q, aq = _q(case, "query"), _q(case, "approved_query")
    if not q or not aq:
        return False
    qs, aqs = _low(q), _low(aq)
    # blessed counts distinct entities; analyst dropped the DISTINCT (or vice versa)
    if ("count(distinct" in aqs.replace(" ", "")) != ("count(distinct" in qs.replace(" ", "")):
        return True
    # both group, but on a different set of columns -> a different grain
    gq, gaq = _group_by_cols(q), _group_by_cols(aq)
    if gq and gaq and gq != gaq:
        return True
    return False


# --------------------------------------------------------------------------------------------------
# Agent-assist hook: the heuristics catch the common signatures; an agent catches the rest by reading
# the recorded trace. The agent's label, when present, wins over the heuristic.
# --------------------------------------------------------------------------------------------------

def build_classification_prompt(case, trace=None):
    """Build a classification PROMPT an agent can answer to label a failed case.

    The agent reads three things, all recorded, none guessed: the recorded TRACE (the action log of
    what the analyst did, step by step), the GOLD (the question and the known answer), and the QUERY
    the analyst ran versus the blessed query. It returns exactly one mode from ERROR_MODES. This is
    how modes the SQL heuristics miss (a subtle reasoning slip the text does not betray) still get
    named, and its answer is merged in via classify_failure with the agent label preferred."""
    trace = trace if trace is not None else case.get("trace", "(no trace recorded)")
    modes = "\n".join(f"  - {m}" for m in ERROR_MODES)
    return f"""You are triaging ONE failed analytics eval case into a single error mode.

Choose exactly one of these modes and reply with only that token:
{modes}

The gold (the known-correct answer this case is judged against):
  question:      {esc(case.get('question'))}
  gold value:    {esc(case.get('gold_value'))}
  metric def:    {esc(case.get('definition') or '(undefined)')}
  blessed query: {esc(case.get('approved_query'))}

What the analyst produced:
  analyst value: {esc(case.get('analyst_value'))}
  analyst query: {esc(case.get('query'))}

The recorded trace (the analyst's action log, step by step):
{esc(trace)}

Read the trace together with the gold and the two queries. Name the single error mode that best
explains why the analyst's value differs from the gold. If none fit, answer: other.
Reply with only the mode token."""


def classify_failure(case, agent_label=None):
    """The merged label: the agent's label when it is a valid mode, otherwise the heuristic.

    `agent_label` may be passed explicitly or carried on the case as case['agent_label']. A label
    outside ERROR_MODES is ignored (a malformed agent answer never silently corrupts a cluster)."""
    label = agent_label if agent_label is not None else case.get("agent_label")
    if label in ERROR_MODES:
        return label
    return classify_error(case)


def cluster_failures(failed_cases):
    """Group failed cases by merged error mode, ranked by cluster size (largest first; ties broken
    by ERROR_MODES order). Returns an ordered dict {mode: [cases]} of only the modes that occurred."""
    clusters = {}
    for case in failed_cases:
        clusters.setdefault(classify_failure(case), []).append(case)
    order = {m: i for i, m in enumerate(ERROR_MODES)}
    ranked = sorted(clusters.items(), key=lambda kv: (-len(kv[1]), order.get(kv[0], 99)))
    return dict(ranked)


# --------------------------------------------------------------------------------------------------
# HTML readout (shared editorial-light look).
# --------------------------------------------------------------------------------------------------

_CLUSTER_CSS = """
 .mode{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px}
 .mode b{font-size:15px}
 .count{background:#fef3c7;color:#92400e;border-radius:12px;padding:2px 10px;font-size:13px;font-weight:600}
 ul.q{margin:6px 0 0;padding-left:18px} ul.q li{font-size:13px;color:#333;padding:2px 0}
 .gap{color:#888;font-size:12px}
"""


def render_clusters_html(clusters, out_path, title="Failure clusters"):
    """Render ranked error-mode clusters as one HTML readout: a card per mode, largest first, each
    showing the mode, its count, a one-line description, and the member questions (with the value gap
    where known). `clusters` is the dict from cluster_failures. Returns out_path."""
    desc = {
        "undefined-metric-drift": "Definitional question, value far from gold, query unlike the blessed one.",
        "fan-out": "Joined order_items and SUM'd an order-level column, so rows multiplied.",
        "wrong-filter": "Dropped status='completed', or counted cancelled/returned rows.",
        "wrong-grain": "Counted at the wrong grain (missing DISTINCT, or grouped differently).",
        "wrong-source": "Read the wrong object (e.g. sessions.had_purchase instead of events).",
        "other": "No signature explained this failure; needs a human (or the agent) to label it.",
    }
    total = sum(len(v) for v in clusters.values())
    cards = []
    for mode, cases in clusters.items():
        items = []
        for c in cases:
            gap = value_gap(c)
            gaptxt = f' <span class="gap">(off by {gap*100:.0f}%)</span>' if gap is not None else ""
            items.append(f"<li>{esc(c.get('question'))}{gaptxt}</li>")
        cards.append(
            f'<div class="card">'
            f'<div class="mode"><b>{esc(mode)}</b><span class="count">{len(cases)}</span></div>'
            f'<div class="gap">{esc(desc.get(mode, ""))}</div>'
            f'<ul class="q">{"".join(items)}</ul>'
            f'</div>')
    sub = (f"{total} failed case{'s' if total != 1 else ''} in "
           f"{len(clusters)} error mode{'s' if len(clusters) != 1 else ''}, ranked by size. "
           f"Fix the biggest cluster first. Gold answers stay hidden with the harness.")
    doc = page(title, sub, "\n".join(cards), extra_css=_CLUSTER_CSS)
    Path(out_path).write_text(doc)
    return out_path
