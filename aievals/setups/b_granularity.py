"""B-granularity Granularity menu (cross-cutting axis, no single layer): resolves FRAMEWORK_v0 §11 D1.

CONTEXT-DECISION-GRID Menu C ("Structure & granularity") leaves one decision open: when the SAME
governed definition is stored, should it live as one contract per metric inside a per-area index, as
a single flat index of all metrics, or domain-bundled and loaded on demand? The grid does not pick a
winner. It says teach all three and "let the ablation harness decide empirically" (CONTEXT-DECISION-
GRID §1C and §6, carried forward as open decision D1 in FRAMEWORK_v0 §11). Track E's campaign (E1) is
the thing assigned to resolve D1, but a campaign can only rank options that something has actually
staged. Nothing else in the plan stages the granularity options, so without this unit E1 has nothing
to rank and the plan must not claim it resolves D1.

This is that unit. It stages the retention definition THREE structural ways while holding its MEANING
fixed (all three are derived from the one canonical retention contract, so the metric's meaning,
numerator, denominator, window, and filters are byte-identical across forms; only the file structure
differs). The three forms are:

  1. per-metric inside a per-area index: a directory (the area, e.g. growth) holding one file per
     metric. The reader globs the directory.
  2. a single flat index: one file holding every metric in a flat list. The reader reads one file.
  3. domain-bundled, loaded on demand: the domain's metrics grouped in a bundle that is read only when
     the question matches the domain. The reader is handed an explicit list (the on-demand load),
     not an auto-resident directory.

build() constructs the three structural fixture forms from the canonical contract and returns the
three Setups the comparison run toggles, so E1 has a per-granularity delta to rank for D1. There is no
result number anywhere: the meaning source carries none, and the structural rewriting adds none. The
figure is computed from the data by the agent at run time, never written into the context.

The honest status is buildable-now: this is pure staging that rides on the existing source-reader, no
new infrastructure. What it does NOT do is decide which granularity wins. That ranking is E1's job and
needs the campaign run; this unit only stakes out the three options so the ranking is possible.
"""
from pathlib import Path

from aievals.harness.setups import Setup
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# The three structural forms of Menu C / D1. Carried as code-level labels so the structure a Setup was
# staged in travels with it and a reader can name what it is looking at, not just guess from the path.
PER_METRIC = "per-metric-in-area-index"
SINGLE_INDEX = "single-flat-index"
DOMAIN_BUNDLED = "domain-bundled-on-demand"
STRUCTURES = (PER_METRIC, SINGLE_INDEX, DOMAIN_BUNDLED)

# The area and domain the worked retention metric belongs to. Used only to organize the per-area index
# and the domain bundle; it is structural metadata, not a result.
AREA = "growth"
DOMAIN = "growth"

# The canonical meaning source: our teaching retention contract, defined by meaning and carrying no
# result number. All three structural forms are rewritten from this one file, which is how MEANING is
# held fixed while only structure varies.
DEFAULT_SOURCE = FIXTURES / "retention_contract.yaml"


def _require_yaml():
    if yaml is None:
        raise RuntimeError("pyyaml required to stage the granularity forms")


def load_meaning(source_contract=None):
    """Read the meaning source (the canonical retention contract by default) and return its metric
    dicts. This is the single MEANING every structural form is built from, so the forms cannot drift
    apart in meaning. `source_contract` lets the caller point at their own contract; it defaults to our
    canonical fixture so the unit is runnable hermetically with no analyst path baked in."""
    _require_yaml()
    src = Path(source_contract) if source_contract is not None else DEFAULT_SOURCE
    doc = yaml.safe_load(Path(src).read_text()) or {}
    return list(doc.get("metrics", []))


def _write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, default_flow_style=False))
    return path


def stage_forms(metrics, staging_dir):
    """Write the three structural forms of the same `metrics` into `staging_dir` and return the
    reader spec for each, keyed by structure label. The forms differ on disk in a way a reader can
    tell apart: per-metric is a DIRECTORY of one file per metric, single-index is a single FILE, and
    domain-bundled is an explicit LIST of bundle files (the on-demand load). Each overlay also carries
    a `structure` marker so the staged content names its own form. No result number is written: only
    the metric dicts from the meaning source, plus structural metadata, go in."""
    _require_yaml()
    root = Path(staging_dir)

    # 1. per-metric inside a per-area index: one file per metric under the area directory.
    per_metric_dir = root / "per_metric" / AREA
    for m in metrics:
        name = m.get("metric", "metric")
        _write(per_metric_dir / f"{name}.yaml",
               {"structure": PER_METRIC, "area": AREA, "metrics": [m]})

    # 2. a single flat index: every metric in one flat file.
    single_index_file = root / "single_index" / "metrics.yaml"
    _write(single_index_file, {"structure": SINGLE_INDEX, "metrics": list(metrics)})

    # 3. domain-bundled, loaded on demand: the domain's metrics grouped in a bundle, read only when
    #    the question matches. The on-demand nature is expressed by handing the reader an explicit
    #    list rather than an auto-globbed resident directory.
    domain_bundle_file = root / "domain_bundled" / "domains" / f"{DOMAIN}.yaml"
    _write(domain_bundle_file,
           {"structure": DOMAIN_BUNDLED, "domain": DOMAIN, "load": "on-demand",
            "metrics": list(metrics)})

    return {
        PER_METRIC: str(per_metric_dir),          # a directory: the reader globs it
        SINGLE_INDEX: str(single_index_file),     # a single file
        DOMAIN_BUNDLED: [str(domain_bundle_file)],  # an explicit list: the on-demand load
    }


def build(source_contract=None, staging_dir=None, **ctx):
    """Build the three structural fixture forms (per-metric-in-area-index, single-flat-index, and
    domain-bundled-on-demand) from one meaning source and return the three Setups the comparison run
    toggles, in that order. They hold MEANING fixed (all rewritten from the same contract) and vary
    only structure, which is exactly what E1 needs to rank for D1.

    `source_contract` defaults to our canonical retention contract (no analyst path baked in).
    `staging_dir` is where the structural forms are written; if omitted, a temporary directory is
    created so the unit runs hermetically. All three Setups stay at layer L3 because the layer is held
    fixed across the arms (the metric-definition layer); only the granularity varies."""
    metrics = load_meaning(source_contract)
    if staging_dir is None:
        import tempfile
        staging_dir = tempfile.mkdtemp(prefix="b_granularity_")
    specs = stage_forms(metrics, staging_dir)
    return [
        Setup(name=PER_METRIC, layer="L3", reader="file", spec=specs[PER_METRIC]),
        Setup(name=SINGLE_INDEX, layer="L3", reader="file", spec=specs[SINGLE_INDEX]),
        Setup(name=DOMAIN_BUNDLED, layer="L3", reader="file", spec=specs[DOMAIN_BUNDLED]),
    ]


def baseline():
    """The no-context baseline the three granularity arms are each compared against: nothing staged,
    so layer is None."""
    return Setup(name="no-granularity", layer=None, reader="file", spec=None)


register_setup(SetupSpec(
    key="B-granularity",
    layer=None,  # cross-cutting: the granularity axis, not a single canonical layer
    status="buildable-now",
    summary=(
        "Stage the same retention definition three structural ways (per-metric in a per-area index, "
        "a single flat index, domain-bundled on demand), holding meaning fixed, so Track E (E1) has "
        "the three arms to rank for open decision D1. Staging only; it does not pick the winner."
    ),
    blocked_on=None,
    source="CONTEXT-DECISION-GRID §1C and §6, FRAMEWORK_v0 §11 D1",
    build=build,
))
