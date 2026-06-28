#!/usr/bin/env python3
"""Tests for aievals/monitor.py — the V7 dashboard reads the run_eval shape (BL-C1 fix).

The bug: render_dashboard read top-level accuracy/git_sha/changelog, but real run records (and the
staged climb fixtures) nest accuracy/passed/total under `aggregate` and may omit git_sha/changelog,
so it KeyError'd. These prove it now normalizes from `aggregate` and tolerates the missing fields."""
import glob
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.monitor import render_dashboard, _run_view


def test_run_view_reads_aggregate_and_tolerates_missing():
    v = _run_view({"run_id": "r1", "timestamp": "t",
                   "aggregate": {"accuracy": 0.8, "passed": 8, "total": 10}})
    assert v["accuracy"] == 0.8 and v["passed"] == 8 and v["total"] == 10
    assert v["git_sha"] == "" and v["changelog"] == ""  # missing fields tolerated, not crashed


def test_render_nested_aggregate_no_crash():
    runs = [
        {"run_id": "baseline", "timestamp": "2026-06-27", "split": "train",
         "aggregate": {"accuracy": 0.55, "passed": 11, "total": 20}},  # no git_sha/changelog
        {"run_id": "after-defs", "timestamp": "2026-06-28", "split": "train",
         "git_sha": "abc1234", "changelog": "defined retention",
         "aggregate": {"accuracy": 0.75, "passed": 15, "total": 20}},
    ]
    with tempfile.TemporaryDirectory() as d:
        out = render_dashboard(runs, Path(d) / "m.html")
        doc = Path(out).read_text()
        assert "55%" in doc and "75%" in doc           # accuracy read from aggregate
        assert "abc1234" in doc and "defined retention" in doc  # meta fields render
        assert "train" in doc                          # split column


def test_render_real_climb_fixtures_no_crash():
    fs = sorted(glob.glob(str(ROOT / "aievals" / "runs" / "climb-*.json")))
    if not fs:
        return  # fixtures optional
    runs = [json.load(open(f)) for f in fs]
    with tempfile.TemporaryDirectory() as d:
        out = render_dashboard(runs, Path(d) / "climb.html")  # must not raise on the real shape
        assert Path(out).exists()
