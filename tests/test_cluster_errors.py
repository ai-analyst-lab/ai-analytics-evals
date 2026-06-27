#!/usr/bin/env python3
"""Tests for aievals.cluster_errors: the rule-based error-mode classifier, the ranked clustering,
the agent-assist merge, and the HTML readout. Hermetic: no warehouse, no network, synthetic cases
only. Run: python3 tests/test_cluster_errors.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.cluster_errors import (
    classify_error, classify_failure, cluster_failures,
    build_classification_prompt, render_clusters_html,
    ERROR_MODES, value_gap, value_is_far, sql_similarity, structurally_different, is_definitional,
)

# --- one synthetic failed case per mode -----------------------------------------------------------

FANOUT = {
    "question": "What is total completed revenue?",
    "gold_value": 3_150_000.0, "analyst_value": 5_900_000.0,
    "query": "SELECT SUM(o.total_amount) FROM orders o JOIN order_items oi ON oi.order_id=o.id WHERE o.status='completed'",
    "approved_query": "SELECT SUM(total_amount) FROM orders WHERE status='completed'",
    "definition": "sum of total_amount over completed orders",
}

WRONG_FILTER = {
    "question": "How many orders last month?",
    "gold_value": 1000.0, "analyst_value": 1450.0,
    "query": "SELECT COUNT(*) FROM orders",
    "approved_query": "SELECT COUNT(*) FROM orders WHERE status='completed'",
    "definition": "count of completed orders",
}

WRONG_FILTER_INCLUDES = {
    "question": "Completed order count?",
    "gold_value": 1000.0, "analyst_value": 1200.0,
    "query": "SELECT COUNT(*) FROM orders WHERE status IN ('completed','cancelled')",
    "approved_query": "SELECT COUNT(*) FROM orders WHERE status='completed'",
    "definition": "count of completed orders",
}

WRONG_GRAIN = {
    "question": "How many customers ordered?",
    "gold_value": 800.0, "analyst_value": 1000.0,
    "query": "SELECT COUNT(customer_id) FROM orders WHERE status='completed'",
    "approved_query": "SELECT COUNT(DISTINCT customer_id) FROM orders WHERE status='completed'",
    "definition": "distinct customers with a completed order",
}

WRONG_SOURCE = {
    "question": "How many purchases?",
    "gold_value": 500.0, "analyst_value": 650.0,
    "query": "SELECT COUNT(*) FROM sessions WHERE had_purchase = true",
    "approved_query": "SELECT COUNT(*) FROM events WHERE event_name='purchase'",
    "definition": "count of purchase events",
}

METRIC_DRIFT = {
    "question": "What is our user retention?",
    "gold_value": 0.253, "analyst_value": 0.91,
    "query": "SELECT COUNT(DISTINCT user_id)*1.0/ (SELECT COUNT(DISTINCT user_id) FROM signups) FROM logins WHERE login_date >= signup_date",
    "approved_query": "SELECT returned.n*1.0/cohort.n FROM (SELECT COUNT(DISTINCT user_id) n FROM activity WHERE day=30) returned, (SELECT COUNT(DISTINCT user_id) n FROM cohort) cohort",
    "definition": "",   # undefined metric: this is the drift case
}

OTHER = {
    "question": "What is average order value?",
    "gold_value": 42.0, "analyst_value": 42.05,
    "query": "SELECT AVG(total_amount) FROM orders WHERE status='completed'",
    "approved_query": "SELECT AVG(total_amount) FROM orders WHERE status='completed'",
    "definition": "mean order value of completed orders",
}


def test_classify_fanout():
    assert classify_error(FANOUT) == "fan-out"


def test_classify_wrong_filter_missing():
    assert classify_error(WRONG_FILTER) == "wrong-filter"


def test_classify_wrong_filter_includes_excluded_states():
    assert classify_error(WRONG_FILTER_INCLUDES) == "wrong-filter"


def test_classify_wrong_grain():
    assert classify_error(WRONG_GRAIN) == "wrong-grain"


def test_classify_wrong_source():
    assert classify_error(WRONG_SOURCE) == "wrong-source"


def test_classify_metric_drift():
    assert classify_error(METRIC_DRIFT) == "undefined-metric-drift"


def test_classify_other():
    assert classify_error(OTHER) == "other"


def test_every_mode_is_reachable():
    seen = {classify_error(c) for c in
            (FANOUT, WRONG_FILTER, WRONG_GRAIN, WRONG_SOURCE, METRIC_DRIFT, OTHER)}
    assert seen == {"fan-out", "wrong-filter", "wrong-grain", "wrong-source",
                    "undefined-metric-drift", "other"}


def test_helpers():
    assert value_gap(WRONG_FILTER) == 0.45
    assert value_is_far(METRIC_DRIFT) is True
    assert value_is_far(OTHER) is False           # within tolerance -> not far
    assert is_definitional(METRIC_DRIFT) is True
    assert is_definitional(OTHER) is False
    assert sql_similarity("SELECT a FROM t", "SELECT a FROM t") == 1.0
    assert structurally_different(METRIC_DRIFT) is True
    assert structurally_different(OTHER) is False  # identical to blessed


def test_cluster_counts_and_ranking():
    cases = [FANOUT, FANOUT, FANOUT, WRONG_FILTER, WRONG_FILTER, WRONG_SOURCE]
    clusters = cluster_failures(cases)
    assert {k: len(v) for k, v in clusters.items()} == {
        "fan-out": 3, "wrong-filter": 2, "wrong-source": 1}
    # ranked largest-first
    assert list(clusters.keys()) == ["fan-out", "wrong-filter", "wrong-source"]


def test_agent_label_merge_prefers_agent():
    # heuristic would say "other"; an agent reading the trace labels it the real mode
    case = dict(OTHER, agent_label="wrong-grain")
    assert classify_failure(case) == "wrong-grain"
    # an explicit arg also wins
    assert classify_failure(OTHER, agent_label="fan-out") == "fan-out"
    # a malformed agent label is ignored, falling back to the heuristic
    assert classify_failure(dict(FANOUT, agent_label="nonsense")) == "fan-out"


def test_agent_label_used_in_clustering():
    cases = [OTHER, dict(OTHER, agent_label="fan-out")]
    clusters = cluster_failures(cases)
    assert set(clusters.keys()) == {"other", "fan-out"}


def test_build_prompt_mentions_trace_gold_and_query():
    prompt = build_classification_prompt(FANOUT, trace="step 1: joined order_items\nstep 2: summed")
    for mode in ERROR_MODES:
        assert mode in prompt
    assert "joined order_items" in prompt          # the recorded trace is in the prompt
    assert str(FANOUT["gold_value"]) in prompt      # the gold is in the prompt
    assert "total_amount" in prompt                 # the query is in the prompt


def test_render_clusters_html(tmp_path=None):
    import tempfile, os
    clusters = cluster_failures([FANOUT, FANOUT, WRONG_FILTER, WRONG_SOURCE, OTHER])
    out = os.path.join(tempfile.mkdtemp(), "clusters.html")
    path = render_clusters_html(clusters, out)
    doc = Path(path).read_text()
    assert doc.startswith("<!doctype html>")
    # every occurring mode is a card heading, with its count
    assert "fan-out" in doc and "wrong-filter" in doc and "other" in doc
    assert ">2<" in doc                              # fan-out count badge
    # member questions are listed
    assert "What is total completed revenue?" in doc
    # the gap annotation rendered for a known gap
    assert "off by" in doc
    # shares the monitor look (the editorial-light card class + page background)
    assert ".card{" in doc and "#fafafa" in doc


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_cluster_errors:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
