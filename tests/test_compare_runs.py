#!/usr/bin/env python3
"""Tests for aievals/compare_runs.py — side-by-side model comparison (D22)."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.compare_runs import compare_runs, render_comparison

RUN_OPUS = {
    "model": "opus-4.8", "split": "train", "context_state": {"n": 2},
    "aggregate": {"accuracy": 0.86, "passed": 12, "total": 14, "avg_query_similarity": 0.65,
                  "avg_latency_ms": 1260, "total_cost": 0.84, "cost_per_correct": 0.07, "total_tokens": 21000},
    "cases": [
        {"question": "total revenue?", "passed": True, "analyst_value": 3150899.34},
        {"question": "retention?", "passed": False, "analyst_value": 0.57},
        {"question": "churn?", "passed": True, "analyst_value": 0.74},
    ],
}
RUN_GLM = {
    "model": "glm-5.2", "split": "train", "context_state": {"n": 2},
    "aggregate": {"accuracy": 0.64, "passed": 9, "total": 14, "avg_query_similarity": 0.55,
                  "avg_latency_ms": 2200, "total_cost": 0.12, "cost_per_correct": 0.013, "total_tokens": 24000},
    "cases": [
        {"question": "total revenue?", "passed": True, "analyst_value": 3150899.34},
        {"question": "retention?", "passed": False, "analyst_value": 0.61},
        {"question": "churn?", "passed": False, "analyst_value": 0.50},   # GLM misses churn -> disagree
    ],
}


def test_compare_runs_structure_and_disagreements():
    c = compare_runs(RUN_OPUS, RUN_GLM)
    assert c["aggregate_a"]["accuracy"] == 0.86 and c["aggregate_b"]["accuracy"] == 0.64
    assert len(c["cases"]) == 3
    # only "churn?" differs (opus pass, glm fail)
    assert c["disagreements"] == 1
    churn = next(x for x in c["cases"] if x["question"] == "churn?")
    assert churn["a_passed"] is True and churn["b_passed"] is False and churn["disagree"] is True


def test_render_comparison_html():
    with tempfile.TemporaryDirectory() as d:
        out = render_comparison(RUN_OPUS, RUN_GLM, Path(d) / "cmp.html")
        doc = Path(out).read_text()
        assert "opus-4.8" in doc and "glm-5.2" in doc          # model labels
        assert "Cost per correct" in doc and "0.07" in doc and "0.013" in doc  # the D22 cell, both
        assert "86.0%" in doc and "64.0%" in doc               # accuracy both
        assert "1 of 3 cases disagree" in doc                  # disagreement summary
