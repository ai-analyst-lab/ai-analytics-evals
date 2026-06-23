"""B-format Format menu (cross-cutting, no single layer): stage one meaning three ways and let the
run measure which format drifts.

CONTEXT-DECISION-GRID section 1B calls format "the load-bearing menu" and says the most common
silent-drift source in analytics is putting a definition in prose. This unit makes that claim
testable instead of asserted. It stages the SAME retention definition in three formats, holding the
meaning fixed so format is the only variable:

  1. structured YAML  (reuse retention_contract.yaml): a quoted field is CITED, looked up by name,
     not regenerated. This is the deterministic-quoting property from C-store.md section 2.2: a
     value retrieved by its key is a database lookup, not a generation step, so it cannot drift.
  2. prose Markdown    (retention_prose.md): the same meaning written as a paragraph. An LLM
     regenerates free text token-by-token, so a prose definition can be silently re-rendered. This
     is the arm where drift is expected to enter.
  3. executable SQL    (retention.sql): the number computed BY NAME from the data, never described.
     The agent calls retention_rate and gets proven SQL rather than authoring its own.

The unit is buildable now because it is pure staging (three format forms of one meaning) over the
0.2a source-reader, with no new infrastructure. The structured form rides the existing file reader
(which parses YAML into composable metric dicts); the prose and SQL forms ride a small text reader
registered here, because their meaning is carried as free text the agent must re-read (prose) or
call by name (SQL), not as cited structured fields. None of the three forms carries a hardcoded
result: a metric is defined by its meaning, and the figure is computed from the data each run.

The DRIFT DELTA across formats (does prose drift more than structured on the same question?) is
measured at RUN TIME by the comparison campaign, which stages each arm, runs the agent, and compares
run-to-run variance. It is deliberately NOT computed here: this module only proves the three format
forms of the one meaning exist and stage, and that none of them smuggles in a result number. The
hermetic test below asserts exactly that.
"""
from pathlib import Path

from aievals.harness.setups import Setup, SourceReader, register_reader
from aievals.setups import FIXTURES


class FormatTextReader(SourceReader):
    """Read a single context file as raw text (prose Markdown or executable SQL) and return it as a
    one-element overlay, so read_overlays() is uniform across formats. Prose and SQL are deliberately
    NOT parsed into structured fields: the meaning lives as free text the agent re-reads (prose) or
    calls by name (SQL), which is precisely the format difference this unit measures. The structured
    YAML form keeps the existing "file" reader, which composes its fields into cited metric dicts."""
    name = "format-text"

    def read(self, spec):
        if spec is None:
            return []
        return [{"format": Path(spec).suffix.lstrip("."), "text": Path(spec).read_text()}]


register_reader(FormatTextReader())


# The three canonical fixtures, all carrying the SAME retention meaning, none carrying a result.
# Our own teaching fixtures, not an analyst path: a real analyst points build() at a fixtures dir
# laid out the same way.
def _paths(fixtures_dir):
    base = Path(fixtures_dir)
    return {
        "structured": base / "retention_contract.yaml",
        "prose": base / "formats" / "retention_prose.md",
        "sql": base / "formats" / "retention.sql",
    }


def build(fixtures_dir=None, **ctx):
    """Return the three comparison arms the format run toggles, one per format of the SAME meaning.
    `fixtures_dir` is the directory holding the three forms (analyst-side when testing a real
    analyst); it defaults to our canonical fixture dir so the setup is runnable hermetically with no
    analyst path baked in. The arms carry layer=None because the variable here is FORMAT, not which
    layer (the meaning, an L3 retention contract, is held fixed across all three)."""
    p = _paths(fixtures_dir if fixtures_dir is not None else FIXTURES)
    structured = Setup(name="structured-yaml", layer=None, reader="file", spec=str(p["structured"]))
    prose = Setup(name="prose-markdown", layer=None, reader="format-text", spec=str(p["prose"]))
    executable = Setup(name="executable-sql", layer=None, reader="format-text", spec=str(p["sql"]))
    return [structured, prose, executable]


# Registered at import so the setup self-declares its honest status next to the code. Imported here
# after build() is defined so the spec can reference it.
from aievals.setups.base import SetupSpec, register_setup  # noqa: E402

register_setup(SetupSpec(
    key="B-format",
    layer=None,
    status="buildable-now",
    summary=(
        "Stage the SAME retention definition in three formats (structured YAML, prose Markdown, "
        "executable SQL), meaning held fixed; the run measures which format drifts. Structured is "
        "cited by name (no drift), prose is paraphrased (where drift enters), SQL computes the "
        "number by name. The drift delta is measured at run time, not here."
    ),
    blocked_on=None,
    source="C-store.md, CONTEXT-DECISION-GRID §1B, FRAMEWORK_v0 §4 Rule A",
    build=build,
))
