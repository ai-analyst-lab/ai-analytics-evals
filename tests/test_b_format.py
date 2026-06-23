#!/usr/bin/env python3
"""Tests for B-format: the same retention meaning staged three ways (structured YAML, prose
Markdown, executable SQL). Hermetic: reads only the canonical teaching fixtures, no warehouse, no
network, no analyst repo. The drift delta across formats is a RUN-TIME measurement and is not
computed here; this test proves the three format forms of the one meaning exist and stage, and that
none of them smuggles in a hardcoded result number. Run: python3 tests/test_b_format.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aievals.setups import b_format as bf
from aievals.setups.base import registry
from aievals.harness.setups import compose_metrics

# A result number, in this domain, surfaces as a percentage or one of the measured answer values.
# (These are the figures the live comparison runs actually produced; none belongs in a meaning-only
# context form.) Spelling-out windows like "ninety days" keeps the fixtures free of stray digits, so
# the check stays principled rather than banning every numeral.
MEASURED_ANSWERS = ("55.4", "33.2", "84.8", "75.2")


def _staged_text(setup):
    """The raw content an arm stages, concatenated, for the no-result-number check."""
    return "".join(str(ov) for ov in setup.read_overlays())


def _has_result_number(text):
    return "%" in text or any(a in text for a in MEASURED_ANSWERS)


# ---- three distinct format forms of one meaning --------------------------------------------------

def test_build_returns_three_distinct_formats():
    arms = bf.build()
    assert len(arms) == 3
    names = [a.name for a in arms]
    assert names == ["structured-yaml", "prose-markdown", "executable-sql"]
    # distinct format forms: distinct readers and distinct underlying files
    readers = {a.reader for a in arms}
    assert readers == {"file", "format-text"}
    assert len({a.spec for a in arms}) == 3
    # format is the variable, not the layer: the meaning (L3 retention contract) is held fixed
    assert all(a.layer is None for a in arms)


def test_each_form_stages_and_carries_the_same_meaning():
    structured, prose, executable = bf.build()

    # 1. structured YAML: the field is parsed and cited by name (deterministic quoting)
    metrics = compose_metrics([], structured.read_overlays())
    assert "retention_rate" in [m["metric"] for m in metrics]

    # 2. prose Markdown: the same meaning as free text the agent must re-read
    prose_text = _staged_text(prose).lower()
    assert "retention" in prose_text
    assert "ninety days" in prose_text and "completed orders" in prose_text

    # 3. executable SQL: the number computed BY NAME, not described
    sql_text = _staged_text(executable)
    assert "retention_rate" in sql_text and "select" in sql_text.lower()
    # it is genuinely executable text, not prose about SQL
    assert "from orders" in sql_text.lower()


def test_no_form_contains_a_result_number():
    for arm in bf.build():
        text = _staged_text(arm)
        assert not _has_result_number(text), f"{arm.name} smuggled in a result number"


def test_format_text_reader_is_pluggable_and_empty_safe():
    r = bf.FormatTextReader()
    assert r.read(None) == []          # nothing staged is nothing read, not an error
    overlays = r.read(str(ROOT / "aievals/setups/fixtures/formats/retention.sql"))
    assert len(overlays) == 1 and overlays[0]["format"] == "sql"
    assert "retention_rate" in overlays[0]["text"]


# ---- honest status carried in code --------------------------------------------------------------

def test_spec_registered_buildable_now_and_cross_cutting():
    spec = registry()["B-format"]
    assert spec.status == "buildable-now"   # a buildable part reports buildable, and is tested above
    assert spec.layer is None               # cross-cutting axis, not a single canonical layer
    assert spec.blocked_on is None
    assert "CONTEXT-DECISION-GRID" in spec.source


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print("test_b_format:")
    passed = failed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print(f"  ok   {t.__name__}")
        except Exception as e:
            failed += 1; print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
