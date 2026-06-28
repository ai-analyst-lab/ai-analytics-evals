#!/usr/bin/env python3
"""Tests for the gold-suite runner (aievals/run_eval.py).

Hermetic: no warehouse. A FakeConn maps each gold SQL to a known number, so resolve_gold returns a
fixed gold and the runner's accuracy + query-similarity math is proven end to end. A synthetic
per-case result set is built so SOME cases pass and SOME fail, with identical / changed / disjoint
queries, and the aggregate is asserted exactly. The HTML render is asserted to write and contain
the headline and the per-case verdicts.

Run: python3 -m pytest tests/test_run_eval.py -q
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals import run_eval as RE
from aievals.run_eval import run_eval, token_overlap_similarity, aggregate, grade_case
from aievals.data.gold import load_gold_cases

passed = failed = 0
def check(name, cond):
    """Assert so pytest fails on a bad check; also count for the __main__ summary."""
    global passed, failed
    if cond:
        passed += 1; print(f"  ok   {name}")
    else:
        failed += 1; print(f"  FAIL {name}")
    assert cond, name


# --- fixtures -------------------------------------------------------------------------------

GOLD_YAML = """cases:
  - question: "What is total revenue?"
    sql: "select sum(total_amount) from orders where status='completed'"
    approved_query: "select sum(total_amount) from orders where status='completed'"
    tables: [orders]
    difficulty: easy
    type: "single-table aggregate"
    status: verified
    confidence: A
    verified_by: shane
    verified_at: 2026-06-26
  - question: "What is the retention rate?"
    sql: "select count_if(is_current)*1.0/count(*) from memberships"
    approved_query: "select count_if(is_current)*1.0/count(*) from memberships"
    tables: [memberships]
    difficulty: medium
    type: "definitional"
    status: verified
    confidence: A
    verified_by: shane
    verified_at: 2026-06-26
  - question: "How many completed orders?"
    sql: "select count(*) from orders where status='completed'"
    approved_query: "select count(*) from orders where status='completed'"
    tables: [orders]
    difficulty: easy
    type: "single-table aggregate"
    status: verified
    confidence: A
    verified_by: shane
    verified_at: 2026-06-26
"""

# Gold values the fake warehouse returns for each gold SQL.
GOLD_VALUES = {
    "select sum(total_amount) from orders where status='completed'": 3150899.34,
    "select count_if(is_current)*1.0/count(*) from memberships": 0.2556,
    "select count(*) from orders where status='completed'": 40234,
}


class _FakeCursor:
    def __init__(self, value): self._value = value
    def fetchone(self): return (self._value,)
    def fetchall(self): return [(self._value,)]


class FakeConn:
    """DuckDB-style connection (has .execute) that returns a pinned value per known SQL."""
    def __init__(self, values): self.values = values
    def execute(self, sql):
        key = sql.strip()
        if key not in self.values:
            raise KeyError(f"FakeConn has no value for SQL: {sql}")
        return _FakeCursor(self.values[key])


def _gold_path(d):
    p = Path(d) / "gold.yaml"
    p.write_text(GOLD_YAML)
    return p


# Synthetic analyst results: case 1 passes (correct value + identical query),
# case 2 fails (wrong value + a changed-but-related query),
# case 3 passes (correct value + a query missing tokens => partial similarity),
# plus an unmatched question that is not in the gold suite.
PER_CASE = [
    {"question": "What is total revenue?",
     "analyst_value": 3150899.34,
     "analyst_query": "select sum(total_amount) from orders where status='completed'"},
    {"question": "What is the retention rate?",
     "analyst_value": 0.99,   # wrong (drifted)
     "analyst_query": "select avg(case when ended_at is null then 1 else 0 end) from memberships"},
    {"question": "How many completed orders?",
     "analyst_value": 40234,
     "analyst_query": "select count(*) from orders"},   # missing the status filter tokens
    {"question": "Some question not in the suite",
     "analyst_value": 1, "analyst_query": "select 1"},
]


# --- tests ----------------------------------------------------------------------------------

def test_token_overlap_similarity_bounds():
    a = "select sum(x) from t"
    check("identical query similarity == 1.0", token_overlap_similarity(a, a) == 1.0)
    check("disjoint query similarity == 0.0",
          token_overlap_similarity("select a from b", "drop table z cascade now") == 0.0)
    partial = token_overlap_similarity("select count(*) from orders",
                                       "select count(*) from orders where status='completed'")
    check("partial overlap strictly between 0 and 1", 0.0 < partial < 1.0)


def test_aggregate_accuracy_and_similarity():
    with tempfile.TemporaryDirectory() as d:
        conn = FakeConn(GOLD_VALUES)
        res = run_eval(_gold_path(d), PER_CASE, conn, out_dir=Path(d) / "runs", run_id="t1")
        agg = res["aggregate"]
        check("graded exactly 3 matched cases (unmatched excluded)", agg["total"] == 3)
        check("2 of 3 pass", agg["passed"] == 2)
        check("1 of 3 fails", agg["failed"] == 1)
        check("accuracy == 2/3 rounded", agg["accuracy"] == round(2 / 3, 4))
        check("one unmatched result captured", res["unmatched"] == ["Some question not in the suite"])

        # avg query similarity matches an independent recompute over the three graded cases.
        sims = [token_overlap_similarity(
                    PER_CASE[i]["analyst_query"],
                    {c.question: c for c in load_gold_cases(_gold_path(d))}[PER_CASE[i]["question"]].approved_query)
                for i in range(3)]
        expected = round(sum(sims) / 3, 4)
        check("avg_query_similarity matches recompute", agg["avg_query_similarity"] == expected)


def test_per_case_signals():
    with tempfile.TemporaryDirectory() as d:
        conn = FakeConn(GOLD_VALUES)
        res = run_eval(_gold_path(d), PER_CASE, conn, out_dir=Path(d) / "runs", run_id="t2")
        by_q = {c["question"]: c for c in res["cases"]}
        rev = by_q["What is total revenue?"]
        check("passing case marked passed", rev["passed"] is True)
        check("passing identical query -> diff identical", rev["query_diff"] == "identical")
        check("passing identical query -> similarity 1.0", rev["query_similarity"] == 1.0)
        ret = by_q["What is the retention rate?"]
        check("wrong value marked failed", ret["passed"] is False)
        check("changed query -> diff changed", ret["query_diff"] == "changed")
        cnt = by_q["How many completed orders?"]
        check("correct value but partial query still passes on accuracy", cnt["passed"] is True)
        check("partial query similarity below 1.0", cnt["query_similarity"] < 1.0)
        check("gold never None for graded cases",
              all(c["gold_value"] is not None for c in res["cases"]))


GOLD_YAML_SPLIT = GOLD_YAML.replace(
    'type: "single-table aggregate"\n    status: verified\n    confidence: A\n    verified_by: shane\n    verified_at: 2026-06-26\n  - question: "What is the retention rate?"',
    'type: "single-table aggregate"\n    split: train\n    status: verified\n    confidence: A\n    verified_by: shane\n    verified_at: 2026-06-26\n  - question: "What is the retention rate?"',
).replace(
    'type: "definitional"\n    status: verified',
    'type: "definitional"\n    split: test\n    status: verified',
).replace(
    'type: "single-table aggregate"\n    status: verified\n    confidence: A\n    verified_by: shane\n    verified_at: 2026-06-26\n',
    'type: "single-table aggregate"\n    split: train\n    status: verified\n    confidence: A\n    verified_by: shane\n    verified_at: 2026-06-26\n',
)


def test_split_filtering():
    """D8: load and grade only the named split; the run JSON records which split it was."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "gold.yaml"; p.write_text(GOLD_YAML_SPLIT)
        check("all cases load when split=None", len(load_gold_cases(p)) == 3)
        tr = load_gold_cases(p, split="train"); te = load_gold_cases(p, split="test")
        check("train split has 2 cases", len(tr) == 2)
        check("test split has 1 case", len(te) == 1)
        check("train cases all tagged train", all(c.split == "train" for c in tr))
        check("test case tagged test", all(c.split == "test" for c in te))
        check("unknown split yields no cases", load_gold_cases(p, split="bogus") == [])
        # run_eval grades only the train split and records it; retention (test) drops to unmatched.
        conn = FakeConn(GOLD_VALUES)
        res = run_eval(p, PER_CASE, conn, out_dir=Path(d) / "runs", run_id="t-split", split="train")
        check("run JSON records the split", res["split"] == "train")
        check("only the 2 train cases graded", res["aggregate"]["total"] == 2)
        check("retention (test) excluded from train run", "What is the retention rate?" in res["unmatched"])


def test_html_and_json_render():
    with tempfile.TemporaryDirectory() as d:
        conn = FakeConn(GOLD_VALUES)
        res = run_eval(_gold_path(d), PER_CASE, conn, out_dir=Path(d) / "runs", run_id="t3")
        hp = Path(res["html_path"]); jp = Path(res["json_path"])
        check("html file written", hp.exists())
        check("json file written", jp.exists())
        doc = hp.read_text()
        check("html has accuracy headline", "accuracy" in doc)
        check("html shows a pass verdict", "PASS" in doc)
        check("html shows a fail verdict", "FAIL" in doc)
        check("html names a question", "What is total revenue?" in doc)
        import json
        loaded = json.loads(jp.read_text())
        check("json carries the aggregate", loaded["aggregate"]["total"] == 3)


if __name__ == "__main__":
    for fn in [test_token_overlap_similarity_bounds, test_aggregate_accuracy_and_similarity,
               test_per_case_signals, test_split_filtering, test_html_and_json_render]:
        print(fn.__name__); fn()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
