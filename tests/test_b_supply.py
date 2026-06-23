#!/usr/bin/env python3
"""Tests for B-supply: the inject-versus-retrieve toggle, the lexical scorer, and the honest
partial status. Hermetic: the toggle runs over a tiny temp corpus of YAML items written to disk,
no warehouse and no analyst repo. The core property under test is that the inject-all arm stages
more items than the retrieve-k arm for the same input set. Run: python3 tests/test_b_supply.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.harness.setups import Setup, compose_metrics
from aievals.setups import b_supply as bs


def _make_corpus(dirpath):
    """Write a small multi-item corpus of meaning-only YAML, no result numbers anywhere. One item
    is rich in the query keyword 'retention' so the lexical scorer has something to rank on."""
    items = {
        "retention.yaml": (
            "metrics:\n"
            "  - metric: retention_rate\n"
            "    means: share of new customers who return; retention of first-time buyers\n"
        ),
        "checkout.yaml": (
            "metrics:\n"
            "  - metric: checkout_conversion\n"
            "    means: share of checkout sessions that complete a purchase\n"
        ),
        "aov.yaml": (
            "metrics:\n"
            "  - metric: average_order_value\n"
            "    means: revenue per completed order\n"
        ),
        "signup.yaml": (
            "metrics:\n"
            "  - metric: signup_rate\n"
            "    means: share of visitors who create an account\n"
        ),
    }
    for name, body in items.items():
        (Path(dirpath) / name).write_text(body)
    return len(items)


# ---- the lexical scorer --------------------------------------------------------------------

def test_lexical_overlap_counts_shared_tokens_and_is_deterministic():
    assert bs.lexical_overlap("retention rate", "the retention rate of buyers") == 2
    assert bs.lexical_overlap("retention", "checkout conversion") == 0
    # an empty query is well-defined (0), not an error
    assert bs.lexical_overlap("", "anything at all") == 0
    # deterministic: same inputs, same score
    assert bs.lexical_overlap("retention", "retention") == bs.lexical_overlap("retention", "retention")


# ---- the core property: inject-all stages MORE than retrieve-k ------------------------------

def test_inject_stages_more_than_retrieve_for_same_input_set():
    with tempfile.TemporaryDirectory() as d:
        n = _make_corpus(d)
        k = 2
        arms = bs.build(items_dir=d, query="retention", k=k)
        assert isinstance(arms, list) and len(arms) == 2
        inject, retrieve = arms
        assert inject.name == "inject-all" and retrieve.name == "retrieve-k"
        n_inject = bs.staged_count(inject)
        n_retrieve = bs.staged_count(retrieve)
        # the toggle's defining behavior: same input set, fewer items staged when retrieving
        assert n_inject == n  # inject-all stages the whole set
        assert n_retrieve == k  # retrieve-k stages exactly the top-k
        assert n_inject > n_retrieve
        # the difference is computed from the inputs (corpus size and k), not hardcoded
        assert n_inject - n_retrieve == n - k


def test_retrieve_picks_the_most_relevant_item():
    with tempfile.TemporaryDirectory() as d:
        _make_corpus(d)
        arm = bs.retrieve_k(items_dir=d, query="retention", k=1)
        overlays = arm.read_overlays()
        names = [m["metric"] for m in compose_metrics([], overlays)]
        # the lexical scorer surfaces the retention item for a retention query, not an arbitrary one
        assert names == ["retention_rate"]


def test_select_top_k_clamps_and_is_deterministic():
    with tempfile.TemporaryDirectory() as d:
        n = _make_corpus(d)
        paths = bs._corpus_paths(d)
        # k above the corpus size clamps to the whole set (never stages more than exists)
        assert len(bs.select_top_k(paths, "retention", k=99)) == n
        # k of zero stages nothing
        assert bs.select_top_k(paths, "retention", k=0) == []
        # same query + k -> same ordering both times
        a = bs.select_top_k(paths, "checkout conversion", k=3)
        b = bs.select_top_k(paths, "checkout conversion", k=3)
        assert a == b


# ---- the canonical fixture default ---------------------------------------------------------

def test_default_uses_meaning_only_fixture_with_no_result_number():
    inject = bs.inject_all()  # defaults to the canonical fixture dir
    overlays = inject.read_overlays()
    metrics = compose_metrics([], overlays)
    assert any(m["metric"] == "retention_rate" for m in metrics)
    # meaning-only: the staged content carries no result number anywhere
    blob = str(overlays)
    assert "55.4" not in blob and "%" not in blob
    # the arms are cross-cutting (no single layer)
    for arm in (bs.inject_all(), bs.retrieve_k()):
        assert isinstance(arm, Setup) and arm.layer is None


# ---- honest status -------------------------------------------------------------------------

def test_spec_is_registered_partial_with_blockers_named():
    from aievals.setups.base import registry
    spec = registry()["B-supply"]
    assert spec.layer is None  # cross-cutting axis
    assert spec.status == "partial"
    assert spec.source == "C-supply-retrieval.md"
    # the honest label: the toggle is buildable, full retrieval and the B6 corrections-tail wait
    assert spec.blocked_on
    assert "retrieval" in spec.blocked_on
    assert "B6" in spec.blocked_on
    # the partial spec still produces runnable arms now
    assert callable(spec.build) and len(spec.build()) == 2


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b_supply:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
