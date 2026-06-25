---
name: adapter-test
description: Inspect the adapter seam, the one way the eval tool talks to an analyst. Use when the user says "/adapter-test", "what analysts can the tool target", "show the registered adapters", "does the missing-target case fail loudly", "prove staging is reversible", or "is the starter adapter ready yet". It shows the registry, that an unknown target raises KeyError, that the ai-analyst-plus adapter stages and restores deterministically against a temp fake repo, and that the starter adapter is registered but blocked on W1.3. The live run step (asking the analyst N times) is agentic and is handed to /reliability.
---

# Skill: Adapter test (the analyst seam)

## Purpose
The adapter is the seam that lets the tool test any analyst through the same three calls (stage,
run, restore) on a pinned model. This skill inspects that seam without touching a live analyst:
which targets are registered, that a missing target fails loudly instead of falling back to the
wrong analyst, that staging a setup is reversible, and which adapters are honestly blocked. The
run step is the only agentic part, so it is handed to `/reliability`.

## Invocation
`/adapter-test` (inspect every registered adapter), or `/adapter-test <name>` to focus on one.

The registered ids are `ai-analyst-plus` (buildable now) and `ai-analyst-starter` (blocked on
W1.3, the starter repo does not exist on disk yet).

## How to run it
Run from `~/projects/ai-analytics-evals`. Import the adapter modules so each self-registers, read
the registry, prove the missing-target KeyError, stage and restore against a temp fake repo, and
show the starter adapter raising its blocked reason.

```python
import tempfile, yaml
from pathlib import Path
import aievals.adapters.ai_analyst_plus     # import registers the adapter
import aievals.adapters.ai_analyst_starter  # import registers the adapter
from aievals.adapters.base import adapter_names, get_adapter

print("registered adapters:", adapter_names())

# 1. A missing target fails loudly, by design (no silent fallback to the wrong analyst).
try:
    get_adapter("does-not-exist")
except KeyError as e:
    print("missing target raised KeyError:", e)

# 2. The ai-analyst-plus adapter stages and restores deterministically (temp fake repo).
with tempfile.TemporaryDirectory() as d:
    mdir = Path(d) / ".knowledge" / "datasets" / "novamart" / "metrics"
    mdir.mkdir(parents=True)
    (mdir / "index.yaml").write_text("metrics:\n  - metric: checkout_conversion\n    means: x\n")
    overlay = Path(d) / "with_retention"; overlay.mkdir()
    (overlay / "retention.yaml").write_text("metrics:\n  - metric: retention\n    means: y\n")
    a = get_adapter("ai-analyst-plus", repo_root=d, dataset="novamart")
    a.stage(str(overlay))
    staged = [m["metric"] for m in yaml.safe_load((mdir / "index.yaml").read_text())["metrics"]]
    a.restore()
    restored = [m["metric"] for m in yaml.safe_load((mdir / "index.yaml").read_text())["metrics"]]
    print("ai-analyst-plus staged:", staged, "restored:", restored)

# 3. The starter adapter is registered but blocked on W1.3, and says so (never silent).
try:
    get_adapter("ai-analyst-starter").stage("any-setup")
except NotImplementedError as e:
    print("ai-analyst-starter blocked:", str(e).split(".")[0])
```

## Present it
Read it as the seam health check. The registry lists every analyst the tool can target. The
KeyError is the safety property: an unknown name stops the run rather than grading the wrong
analyst. The stage then restore round trip shows staging composes base plus overlay and rolls back
to base, so a comparison leaves the analyst exactly as it found it. The starter line is the honest
boundary: the adapter is registered so the model-plurality seam can resolve it by name, but it is
blocked on W1.3 (the ai-analyst-starter repo is not built), and every job raises that reason
instead of silently doing nothing. The third call, `run` (ask the analyst N times), is agentic and
not run here: hand it to `/reliability` in `~/projects/ai-analyst-plus`, which the user runs live.
