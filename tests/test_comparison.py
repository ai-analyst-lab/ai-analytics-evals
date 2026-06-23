#!/usr/bin/env python3
"""Tests for the comparison harness and the shared stats.

Hermetic: the fixtures are the real measured values from the first live run (retention on
NovaMart), so the test proves the math end to end with no warehouse and no analyst repo.
The no-definition setup drifted across 84.8 and 75.2 percent with zero definition citations;
the with-definition setup converged to 55.4 percent with every run citing the definition.

Run: python3 tests/test_comparison.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.stats.reliability import compute
from aievals.harness import comparison

# Real measured first-run results, used as fixtures.
NO_DEFINITION = [
    {"run": 1, "headline": "84.8%", "measured": "customers with 2+ completed orders / 1+; lifetime", "definition_source": "my own choice"},
    {"run": 2, "headline": "84.8%", "measured": "2+/1+ completed orders; full range", "definition_source": "my own choice"},
    {"run": 3, "headline": "84.8%", "measured": "lifetime repeat-purchase rate", "definition_source": "my own choice"},
    {"run": 4, "headline": "75.2%", "measured": "active in both H1 and H2 2024", "definition_source": "my own choice"},
    {"run": 5, "headline": "84.8%", "measured": "2+/1+ completed orders; full 2024", "definition_source": "my own choice"},
]
WITH_DEFINITION = [
    {"run": i, "headline": "55.4%", "measured": "143/258; 90-day repeat purchase; per customer", "definition_source": "metric dictionary"}
    for i in range(1, 6)
]

passed = failed = 0
def check(name, cond):
    global passed, failed
    if cond: passed += 1; print(f"  ok   {name}")
    else: failed += 1; print(f"  FAIL {name}")


def test_no_definition_drifts():
    s = compute(NO_DEFINITION)
    check("no-definition setup DRIFTs", s["verdict"] == "DRIFT")
    check("no-definition has multiple readings", s["n_distinct"] >= 2)
    check("no-definition cited a definition zero times", s["used_dictionary"] == 0)


def test_with_definition_converges():
    s = compute(WITH_DEFINITION)
    check("with-definition setup is STABLE", s["verdict"] == "STABLE")
    check("with-definition cited the definition every run", s["used_dictionary"] == 5)


def test_delta_moves_the_answer():
    result = comparison.comparison_delta([
        {"name": "no-definition", "runs": NO_DEFINITION},
        {"name": "with-retention-definition", "runs": WITH_DEFINITION},
    ])
    d = result["deltas"][0]
    check("verdict changes DRIFT -> STABLE", d["verdict_change"] == "DRIFT -> STABLE")
    check("distinct readings removed", d["distinct_drop"] >= 1)
    check("definition citations gained = 5", d["dictionary_gain"] == 5)
    check("the definition setup moves the answer", d["moves_the_answer"] is True)


def test_report_writes():
    import tempfile
    result = comparison.comparison_delta([
        {"name": "no-definition", "runs": NO_DEFINITION},
        {"name": "with-retention-definition", "runs": WITH_DEFINITION},
    ])
    with tempfile.TemporaryDirectory() as d:
        report = comparison.write_report(d, "What is our retention rate?", result)
        check("report file written", report.exists())
        check("report names the moves-the-answer finding", "moves the answer: True" in report.read_text())


def test_adapter_imports_and_stages_offline():
    """The adapter imports and its staging composes overlays (using a temp fake repo)."""
    import tempfile
    from aievals.adapters.ai_analyst_plus import AIAnalystPlusAdapter
    with tempfile.TemporaryDirectory() as d:
        mdir = Path(d) / ".knowledge" / "datasets" / "novamart" / "metrics"
        mdir.mkdir(parents=True)
        (mdir / "index.yaml").write_text("metrics:\n  - metric: checkout_conversion\n    means: x\n")
        setup = Path(d) / "with_retention"
        setup.mkdir()
        (setup / "retention.yaml").write_text("metrics:\n  - metric: retention\n    means: y\n")
        a = AIAnalystPlusAdapter(repo_root=d, dataset="novamart")
        a.stage(str(setup))
        import yaml
        names = [m["metric"] for m in yaml.safe_load((mdir / "index.yaml").read_text())["metrics"]]
        check("adapter stage composes base + overlay", names == ["checkout_conversion", "retention"])
        a.restore()
        names = [m["metric"] for m in yaml.safe_load((mdir / "index.yaml").read_text())["metrics"]]
        check("adapter restore returns to base", names == ["checkout_conversion"])


if __name__ == "__main__":
    print("test_comparison:")
    test_no_definition_drifts()
    test_with_definition_converges()
    test_delta_moves_the_answer()
    test_report_writes()
    test_adapter_imports_and_stages_offline()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
