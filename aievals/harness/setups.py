"""The generalized setup mechanism: toggle any context layer on or off, and read a layer's
content from any home.

A "setup" used to mean one thing: a metric-definition overlay. This generalizes it. A setup
names a context LAYER (L0-L6 of the canonical stack) and the SOURCE its content is read from.
The comparison run can then stage layer X on, run, stage it off, run, and measure what
toggling that layer did, for any layer, not just the metric definition.

Two pieces:
  - the layer registry (LAYERS): the one canonical L0-L6 vocabulary, so a setup and the adapter
    speak the same names and nothing is mis-wired.
  - the source-reader interface (0.2a): a setup's content can live in a file, a warehouse table,
    or a doc. A reader knows how to fetch the content from its home and hand it back as
    composable overlays. stage() composes and restores; the reader is what changes per home.
    The file reader runs in the eval tool; warehouse and Notion readers run analyst-side (they
    hold the credentials), so the eval tool stays credential-free.
"""
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# The canonical Context Stack (FRAMEWORK_v0 section 2). One vocabulary for every setup, so the
# layer-by-layer B units and the adapter never mis-wire a layer.
LAYERS = {
    "L0": "model / system: the agent plus its system prompt",
    "L1": "company: products, org model, pricing, strategy, the org glossary",
    "L2": "team / org: team structure, initiatives, forums",
    "L3": "area / domain: per-area metric contracts, open questions",
    "L4": "data infrastructure: schemas, joins, shared dimensions, query templates",
    "L5": "corrections / learnings: the mistake log, accumulated memory",
    "L6": "session / task: the live question, the plan, the conversation",
}


class SourceReader:
    """Reads a context layer's content from its home and returns it as a list of overlay dicts
    (the shape stage() composes). Subclass per home. The file reader runs in the eval tool;
    warehouse and Notion readers run analyst-side, behind the adapter, so the tool holds no
    credentials."""
    name = "base"

    def read(self, spec):
        raise NotImplementedError


class FileReader(SourceReader):
    """Read overlays from *.yaml files (a directory, a single file, or an explicit list). This
    is the current staging path, refactored behind the reader interface so a different home can
    be swapped in without touching stage()."""
    name = "file"

    def read(self, spec):
        if yaml is None:
            raise RuntimeError("pyyaml required for the file reader")
        if spec is None:
            return []
        paths = []
        if isinstance(spec, (list, tuple)):
            paths = [Path(x) for x in spec]
        else:
            p = Path(spec)
            if p.is_dir():
                paths = sorted(p.glob("*.yaml"))
            elif p.exists():
                paths = [p]
        return [yaml.safe_load(Path(p).read_text()) or {} for p in paths]


_READERS = {}


def register_reader(reader):
    """Register a source-reader instance by its .name. Self-declaring, so a new home's reader is
    added without editing a central list."""
    _READERS[reader.name] = reader
    return reader


def get_reader(name):
    if name not in _READERS:
        raise KeyError(f"no source-reader named {name!r}; registered: {sorted(_READERS)}")
    return _READERS[name]


def reader_names():
    return sorted(_READERS)


register_reader(FileReader())


@dataclass
class Setup:
    """A context setup the comparison run can toggle.

    name    a label for the arm ("with-retention-definition", "no-context")
    layer   which canonical layer this setup touches (one of LAYERS), or None for the bare baseline
    reader  which source-reader fetches the content ("file" now; "warehouse"/"notion" analyst-side)
    spec    what the reader needs (a dir of yaml, a table name, a page id)
    """
    name: str
    layer: str = None
    reader: str = "file"
    spec: object = None

    def __post_init__(self):
        if self.layer is not None and self.layer not in LAYERS:
            raise ValueError(f"unknown layer {self.layer!r}; must be one of {sorted(LAYERS)}")

    def read_overlays(self):
        """Fetch this setup's content via its source-reader, as composable overlay dicts."""
        return get_reader(self.reader).read(self.spec)


def compose_metrics(base_metrics, overlays):
    """Compose a base metric list with overlay dicts that each carry their own `metrics` list.
    This is the metric-dictionary composition the adapter performs, factored out so any reader's
    overlays compose the same way regardless of which home they came from."""
    metrics = list(base_metrics)
    for ov in overlays:
        metrics.extend((ov or {}).get("metrics", []))
    return metrics
