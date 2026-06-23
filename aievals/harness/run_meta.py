"""Run metadata: every run records quality, speed, and usage, not just quality.

The reliability stats capture quality (does the answer hold). The architecture promised speed
(wall-clock) and usage (tokens, and the cost computed from them) on every run too. This is the
small recorder for those. Cost is computed from tokens times the model's published rate, never
guessed; a model not in the rate table records its tokens with cost left None rather than
inventing a rate.
"""
import time
from dataclasses import dataclass, asdict

# Published per-million-token rates (USD), input and output. Cost is computed, never estimated;
# a model not listed here records tokens with cost=None.
MODEL_RATES = {
    "claude-opus-4-8": {"input": 5.0, "output": 25.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
}


def cost_usd(model, input_tokens, output_tokens):
    """Cost of one run, computed from the model's published rate. None for an unknown model."""
    rate = MODEL_RATES.get(model)
    if rate is None:
        return None
    return round(input_tokens / 1e6 * rate["input"] + output_tokens / 1e6 * rate["output"], 6)


@dataclass
class RunMeta:
    model: str = None
    seconds: float = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = None

    def as_dict(self):
        return asdict(self)


class timed:
    """Context manager that records wall-clock seconds and, given token counts, cost.

        with timed("claude-opus-4-8") as m:
            ... do the run ...
            m.input_tokens = 1200
            m.output_tokens = 300
        # m.seconds and m.cost_usd are filled on exit

    The clock is injectable so tests are deterministic.
    """
    def __init__(self, model=None, clock=time.perf_counter):
        self._clock = clock
        self.meta = RunMeta(model=model)

    def __enter__(self):
        self._t0 = self._clock()
        return self.meta

    def __exit__(self, *exc):
        self.meta.seconds = round(self._clock() - self._t0, 4)
        self.meta.cost_usd = cost_usd(self.meta.model, self.meta.input_tokens, self.meta.output_tokens)
        return False
