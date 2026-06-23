#!/usr/bin/env python3
"""Tests for Layer 0: the foundation every grader and setup plugs into.

Covers 0.1 (grader interface, six-family registry, four-rung selector), 0.2 (generalized
setups + layer registry), 0.2a (source-reader interface), 0.3 (run metadata), 0.4 (validity
controls), and the 0.5 adapter/model-plurality seam. Hermetic: no warehouse, no analyst repo.

Run: python3 tests/test_layer0.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.graders import base as gb
from aievals.harness import setups as su
from aievals.harness import run_meta as rm
from aievals.harness import controls as ct
from aievals.adapters import base as ab


# ---- 0.1 grader interface ------------------------------------------------------------------

def test_fake_grader_conforms():
    """A fake grader implements the interface and returns the right shape."""
    @gb.register
    class FakeGrader(gb.Grader):
        name = "fake-conform"
        family = "computable"
        truth_basis = "computable"
        surface = "number"
        cost_tier = "operational"

        def grade(self, output, *, intensity="decision-grade", run_type="single-number", **ctx):
            return self.result(kind="score", status="pass", value=1.0, detail="ok")

    g = FakeGrader()
    res = g.grade({"number": 1})
    assert res.family == "computable"
    assert res.truth_basis == "computable"
    assert res.kind == "score" and res.status == "pass" and res.value == 1.0
    assert res.as_dict()["grader"] == "fake-conform"
    assert "fake-conform" in gb.registry()


def test_result_rejects_bad_fields():
    """The result shape validates family, kind, truth_basis, and status."""
    for kwargs in [
        dict(family="not-a-family", kind="score", truth_basis="computable", status="pass"),
        dict(family="computable", kind="not-a-kind", truth_basis="computable", status="pass"),
        dict(family="computable", kind="score", truth_basis="bogus", status="pass"),
        dict(family="computable", kind="score", truth_basis="computable", status="bogus"),
    ]:
        try:
            gb.GraderResult(grader="x", surface="number", **kwargs)
            assert False, f"expected ValueError for {kwargs}"
        except ValueError:
            pass


def test_register_rejects_unknown_family():
    try:
        @gb.register
        class Bad(gb.Grader):
            name = "bad-family"
            family = "nope"
            truth_basis = "computable"
            surface = "number"
        assert False, "expected ValueError on unknown family"
    except ValueError:
        pass


def test_six_families_and_empty_slot():
    """The family table lists all six families; a family with no member shows as an empty list."""
    table = gb.family_table()
    assert set(table) == set(gb.FAMILIES)
    assert len(gb.FAMILIES) == 6
    # outcome-lookup has no buildable member in Layer 0; it must be present but empty here.
    assert table["outcome-lookup"] == []
    assert gb.by_family("outcome-lookup") == []


def test_selector_all_four_rungs():
    """The selector returns one at exploratory, one-or-two at operational, the full set at
    decision-grade, and the full set plus heavy at audit-grade."""
    class E(gb.Grader):
        name = "e"; family = "computable"; truth_basis = "computable"; surface = "n"; cost_tier = "exploratory"
    class O(gb.Grader):
        name = "o"; family = "computable"; truth_basis = "computable"; surface = "n"; cost_tier = "operational"
    class D1(gb.Grader):
        name = "d1"; family = "computable"; truth_basis = "computable"; surface = "n"; cost_tier = "decision-grade"
    class D2(gb.Grader):
        name = "d2"; family = "inspection"; truth_basis = "presence"; surface = "n"; cost_tier = "decision-grade"
    class A(gb.Grader):
        name = "a"; family = "judge"; truth_basis = "expert"; surface = "n"; cost_tier = "audit-grade"; heavy = True

    pool = [E, O, D1, D2, A]
    assert [g.name for g in gb.select_graders(pool, "exploratory")] == ["e"]
    op = gb.select_graders(pool, "operational")
    assert 1 <= len(op) <= 2 and [g.name for g in op] == ["e", "o"]
    dg = gb.select_graders(pool, "decision-grade")
    assert {g.name for g in dg} == {"e", "o", "d1", "d2"}  # full set, no heavy
    ag = gb.select_graders(pool, "audit-grade")
    assert {g.name for g in ag} == {"e", "o", "d1", "d2", "a"}  # full set plus heavy


# ---- 0.2 / 0.2a generalized setups + source-reader -----------------------------------------

def test_file_reader_matches_legacy_composition():
    """The file reader returns overlays that compose to the same dictionary the adapter built."""
    with tempfile.TemporaryDirectory() as d:
        setup = Path(d) / "with_retention"
        setup.mkdir()
        (setup / "retention.yaml").write_text("metrics:\n  - metric: retention\n    means: y\n")
        overlays = su.FileReader().read(str(setup))
        metrics = su.compose_metrics([{"metric": "checkout_conversion"}], overlays)
        assert [m["metric"] for m in metrics] == ["checkout_conversion", "retention"]


def test_second_reader_registers_without_touching_stage():
    """A new home's reader can be registered and selected through the Setup, no stage() change."""
    class FakeWarehouseReader(su.SourceReader):
        name = "fake-warehouse"
        def read(self, spec):
            return [{"metrics": [{"metric": spec, "means": "from a table row"}]}]

    su.register_reader(FakeWarehouseReader())
    assert "fake-warehouse" in su.reader_names()
    s = su.Setup(name="snowflake-arm", layer="L3", reader="fake-warehouse", spec="retention")
    overlays = s.read_overlays()
    metrics = su.compose_metrics([], overlays)
    assert metrics == [{"metric": "retention", "means": "from a table row"}]


def test_setup_validates_layer():
    su.Setup(name="ok", layer="L3")  # valid
    su.Setup(name="bare-baseline", layer=None)  # the no-context baseline is allowed
    try:
        su.Setup(name="bad", layer="L9")
        assert False, "expected ValueError on unknown layer"
    except ValueError:
        pass
    assert set(su.LAYERS) == {"L0", "L1", "L2", "L3", "L4", "L5", "L6"}


# ---- 0.3 run metadata ----------------------------------------------------------------------

def test_run_records_time_and_tokens():
    clock = iter([10.0, 10.5]).__next__
    with rm.timed("claude-opus-4-8", clock=clock) as m:
        m.input_tokens = 1_000_000
        m.output_tokens = 1_000_000
    assert m.seconds == 0.5
    # cost computed from the published rate, never guessed: 1M in * $5 + 1M out * $25 = $30.
    assert m.cost_usd == 30.0


def test_unknown_model_records_tokens_without_inventing_cost():
    with rm.timed("some-unlisted-model", clock=iter([0.0, 1.0]).__next__) as m:
        m.input_tokens = 500
        m.output_tokens = 500
    assert m.seconds == 1.0
    assert m.cost_usd is None  # no rate, so no invented number


# ---- 0.4 validity controls -----------------------------------------------------------------

def test_held_out_refuses_overlap():
    ct.assert_held_out(["q1", "q2"], ["q3", "q4"])  # disjoint passes
    try:
        ct.assert_held_out(["q1", "q2"], ["q2", "q3"])
        assert False, "expected ValidityError on overlap"
    except ct.ValidityError:
        pass


def test_model_pin_refuses_mismatch():
    ct.assert_model_pinned([{"model": "m1"}, {"model": "m1"}])  # same model passes
    for arms in [[{"model": "m1"}, {"model": "m2"}], [{"model": "m1"}, {"model": None}]]:
        try:
            ct.assert_model_pinned(arms)
            assert False, f"expected ValidityError for {arms}"
        except ct.ValidityError:
            pass


def test_noise_floor_and_sub_noise_delta():
    """A delta below the run-to-run baseline spread is not distinguishable from noise."""
    a = [{"headline": "55.4%"}, {"headline": "55.5%"}, {"headline": "55.4%"}]
    b = [{"headline": "55.6%"}, {"headline": "55.4%"}, {"headline": "55.5%"}]
    floor = ct.noise_floor(a, b, metric="mean")
    assert floor is not None and floor >= 0.0
    assert ct.distinguishable(floor * 0.5, floor) is False   # sub-noise: not an effect
    assert ct.distinguishable(floor + 10.0, floor) is True   # well above noise: a real effect


# ---- 0.5 adapter / model plurality seam ----------------------------------------------------

def test_adapter_takes_model_and_routes_by_name():
    # importing the adapter modules registers them
    from aievals.adapters import ai_analyst_plus, ai_analyst_starter  # noqa: F401
    assert "ai-analyst-plus" in ab.adapter_names()
    assert "ai-analyst-starter" in ab.adapter_names()
    a = ab.get_adapter("ai-analyst-plus").with_model("claude-opus-4-8")
    assert a.model == "claude-opus-4-8"


def test_missing_adapter_fails_loudly():
    try:
        ab.get_adapter("no-such-analyst")
        assert False, "expected KeyError on a missing target"
    except KeyError:
        pass


def test_starter_adapter_is_blocked_not_silent():
    """The starter target is registered but blocked on W1.3, and says so loudly."""
    from aievals.adapters.ai_analyst_starter import AIAnalystStarterAdapter
    a = AIAnalystStarterAdapter()
    for call in (lambda: a.stage("x"), lambda: a.run("q"), a.restore):
        try:
            call()
            assert False, "expected NotImplementedError (blocked on W1.3)"
        except NotImplementedError as e:
            assert "W1.3" in str(e)


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_layer0:")
    passed = failed = 0
    for t in TESTS:
        try:
            t()
            passed += 1
            print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
