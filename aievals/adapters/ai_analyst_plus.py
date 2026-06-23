"""Adapter for the ai-analyst-plus analyst.

Knowledge and data live with the analyst (the ai-analyst-plus repo), so this adapter is the
bridge to it. It implements the two deterministic jobs, staging a setup by composing the
analyst's metric dictionary and restoring it, and points at the live agent loop for the third.

Staging reads the setup's content through a source-reader (Layer 0.2a), so the SAME layer can be
staged from a different home (a warehouse table, a Notion page) without changing how stage()
composes and restores. Today the file reader runs here; the warehouse and Notion readers run on
the analyst side (they hold the credentials), so this tool never gets credentials.

The run step (ask the analyst n independent times) is agentic: in ai-analyst-plus it is the
reliability skill, which spawns n fresh-context sub-agents that query the warehouse and report
back. That cannot be driven from plain Python here, so run() raises with the exact instruction.
The deterministic core of the tool, the comparison delta and the stats, works without it: you
stage a setup, the reliability skill produces the runs, and the comparison harness reads them.
"""
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from aievals.adapters.base import AnalystAdapter, register_adapter
from aievals.harness.setups import FileReader, Setup, compose_metrics

# Default location of the analyst repo. Override via AIAnalystPlusAdapter(repo_root=...).
DEFAULT_REPO_ROOT = Path.home() / "projects" / "ai-analyst-plus"


@register_adapter
class AIAnalystPlusAdapter(AnalystAdapter):
    name = "ai-analyst-plus"

    def __init__(self, repo_root=DEFAULT_REPO_ROOT, dataset="novamart", model=None):
        super().__init__(model=model)
        self.repo_root = Path(repo_root)
        self.dataset = dataset

    def _metrics_dir(self):
        return self.repo_root / ".knowledge" / "datasets" / self.dataset / "metrics"

    def _read_overlays(self, setup):
        """Fetch a setup's overlays via its source-reader. A Setup uses its declared reader; a
        plain directory or list of files uses the file reader (the legacy, backward-compatible
        path). None or empty is the no-context baseline."""
        if setup is None:
            return []
        if isinstance(setup, Setup):
            return setup.read_overlays()
        return FileReader().read(setup)

    def stage(self, setup):
        """Compose the active metric dictionary = base index + this setup's overlays.

        `setup` is a directory of *.yaml overlay files, or a Setup whose source-reader fetches
        the content from its home. The base dictionary is snapshotted once to index.base.yaml so
        staging is always reversible; a crash cannot corrupt the base.
        """
        if yaml is None:
            raise RuntimeError("pyyaml required for staging")
        metrics_dir = self._metrics_dir()
        base_path = metrics_dir / "index.base.yaml"
        live_path = metrics_dir / "index.yaml"
        if not base_path.exists():
            base_path.write_text(live_path.read_text())
        base = yaml.safe_load(base_path.read_text()) or {"metrics": []}
        overlays = self._read_overlays(setup)
        metrics = compose_metrics(base.get("metrics", []), overlays)
        live_path.write_text(yaml.safe_dump({"metrics": metrics}, sort_keys=False))
        return live_path

    def restore(self):
        """Put the metric dictionary back to the snapshotted base."""
        metrics_dir = self._metrics_dir()
        base_path = metrics_dir / "index.base.yaml"
        if base_path.exists():
            (metrics_dir / "index.yaml").write_text(base_path.read_text())

    def run(self, question, n=5, model=None):
        pinned = model or self.model
        on_model = f" on model {pinned}" if pinned else ""
        raise NotImplementedError(
            "The run step is agentic. In ai-analyst-plus, run the reliability skill "
            f'(/reliability "{question}" {n}){on_model} under the staged setup; it spawns n '
            "fresh-context sub-agents, queries the warehouse, and writes the runs. "
            "Then feed the resulting runs.json to the comparison harness "
            "(aievals.harness.comparison)."
        )
