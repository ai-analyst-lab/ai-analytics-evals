"""Adapter for the ai-analyst-starter analyst (the public on-ramp).

This is the second concrete adapter the model-plurality seam (Layer 0.5) needs, so that a
comparison can target more than one analyst and A4 multi-model triangulation has somewhere to
route. It is registered so the seam can resolve it by name, but it is BLOCKED on W1.3: the
ai-analyst-starter repo does not exist on disk yet. Every job fails loudly with that reason
rather than silently doing nothing, which is the honest behavior for a not-yet-built target.
"""
from pathlib import Path

from aievals.adapters.base import AnalystAdapter, register_adapter

DEFAULT_REPO_ROOT = Path.home() / "projects" / "ai-analyst-starter"

_BLOCKED = (
    "ai-analyst-starter adapter is blocked on W1.3: the repo does not exist on disk yet "
    "({root}). It is registered so the model-plurality seam can resolve it by name, but it "
    "cannot stage, run, or restore until the starter repo is built."
)


@register_adapter
class AIAnalystStarterAdapter(AnalystAdapter):
    name = "ai-analyst-starter"

    def __init__(self, repo_root=DEFAULT_REPO_ROOT, dataset="novamart", model=None):
        super().__init__(model=model)
        self.repo_root = Path(repo_root)
        self.dataset = dataset

    def _blocked(self):
        return NotImplementedError(_BLOCKED.format(root=self.repo_root))

    def stage(self, setup):
        raise self._blocked()

    def run(self, question, n=5, model=None):
        raise self._blocked()

    def restore(self):
        raise self._blocked()
