"""The adapter: the one way the eval tool talks to an analyst.

The tool never touches data or knowledge directly. An adapter is a small bridge that knows how
to drive one specific analyst. This is the seam that lets the tool test any analyst, ours or a
hosted one, through the same three calls, and on a pinned model so a comparison's delta is
attributable to context and not to a silent model swap.
"""


class AnalystAdapter:
    """Base class for an analyst adapter. Subclass it for a specific analyst.

    Three jobs, nothing more:
      stage(setup)      put the analyst into a setup (for example, add a metric definition),
                        reversibly. A setup is a directory of overlay files, or a Setup object
                        whose source-reader fetches the content from its home.
      run(question, n)  ask the analyst the question n independent times under the current setup
                        and the pinned model, returning a list of n blocks, each:
                          {"headline": <the number>,
                           "measured": <one line: numerator, denominator, grain, window, filter>,
                           "definition_source": "metric dictionary" | "my own choice"}
                        That block shape is exactly what the stats consume.
      restore()         put the analyst back the way it was before staging.

    The model is part of the seam (Layer 0.5): set it at construction or with with_model(), so a
    comparison can pin one model id across both arms (see harness.controls.assert_model_pinned).
    """

    name = "base"

    def __init__(self, model=None):
        self.model = model

    def with_model(self, model):
        """Pin this adapter to a specific model id and return self, for chaining."""
        self.model = model
        return self

    def stage(self, setup):
        raise NotImplementedError

    def run(self, question, n=5, model=None):
        raise NotImplementedError

    def restore(self):
        raise NotImplementedError


_ADAPTERS = {}


def register_adapter(cls):
    """Register an adapter class by its .name. Self-declaring, so a new analyst's adapter is
    added without editing a central list."""
    _ADAPTERS[cls.name] = cls
    return cls


def get_adapter(name, **kw):
    """Resolve a registered adapter by name. A missing target fails loudly, by design: the eval
    tool should never silently fall back to the wrong analyst."""
    if name not in _ADAPTERS:
        raise KeyError(f"no adapter named {name!r}; registered: {sorted(_ADAPTERS)}")
    return _ADAPTERS[name](**kw)


def adapter_names():
    return sorted(_ADAPTERS)
