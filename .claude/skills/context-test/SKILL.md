---
name: context-test
description: Toggle one context-stack layer (a Track B setup) on and off and show exactly what it stages. Use when the user says "/context-test", "toggle the metric definition", "what does the corrections layer add", "show the with and without arms for B4-schema", "did the glossary fire", or wants to inspect a single setup before paying for a full comparison run. It runs the deterministic part (build the with arm and the baseline, show the staged content differs, run the recall precheck on the analyst's run blocks) and hands the did-it-move-the-answer delta to /compare as the user's live run. Parameterized by setup key: B0-system, B1c-company-glossary, B3-metric-definition, B4-schema, B5-query-patterns, B6-corrections, B7-task-scoping.
---

# Skill: Context-test (toggle one layer, see what it does)

## Purpose
Take one context-stack setup and make it concrete: build the with arm and the baseline, show that
the staged content actually differs, and run the cheap recall precheck to see whether the context
fired in the analyst's runs. The by-hand way to understand a single Track B layer before spending a
full comparison run on it. The companion is `/compare`, which measures the delta the toggle made.

## Invocation
`/context-test <setup-key>`

The keys are the registered setups: B0-system, B1c-company-glossary, B3-metric-definition,
B4-schema, B5-query-patterns, B6-corrections, B7-task-scoping. If the user names a layer loosely
("the metric definition one"), map it to the key.

## How to run it
Run from `~/projects/ai-analytics-evals` (no path insert). Populate the registry, build both arms,
diff the staged content, and run the recall precheck on the analyst's run blocks.

```python
import importlib
from aievals.setups import load_all as load_setups, registry
from aievals.harness.recall import context_recall

load_setups()

KEY = "B3-metric-definition"   # swap for any key above (e.g. "B6-corrections")
MARKER = "dictionary"          # substring a run cites when this layer fires ("correction" for B6)
RUNS = [                       # replace with the analyst's real run blocks (W0.3 receipts)
    {"definition_source": "novamart metric dictionary: retention contract"},
    {"definition_source": "ad-hoc, no source cited"},
]

spec = registry()[KEY]
print(f"{KEY}  layer={spec.layer}  status={spec.status}")
print(f"  {spec.summary}")
if spec.blocked_on:
    print(f"  blocked_on: {spec.blocked_on}")

mod = importlib.import_module("aievals.setups." + KEY.lower().replace("-", "_"))
with_arm = mod.build()
if isinstance(with_arm, list):     # multi-arm setups (B7) return [narrow, broad]; take the first
    with_arm = with_arm[0]
base_arm = mod.baseline()

with_content = with_arm.read_overlays()
base_content = base_arm.read_overlays()
print(f"  with arm  {with_arm.name!r} (layer {with_arm.layer}): {len(with_content)} overlay(s) staged")
print(f"  baseline  {base_arm.name!r} (layer {base_arm.layer}): {len(base_content)} overlay(s) staged")
print(f"  staged content differs: {with_content != base_content}")

rc = context_recall(RUNS, marker=MARKER)
print(f"  recall precheck: cited {rc['cited']}/{rc['n']} runs, recall={rc['recall']}, "
      f"fired={rc['fired']}, full_recall={rc['full_recall']}")
```

`RUNS` is illustrative; replace it with the analyst's real run blocks so recall reads real
citations. With no runs to hand, the build-and-diff alone still proves the toggle stages content.

## Present it
Show the key, its layer and status, whether the with arm stages more overlays than the baseline
(staged content differs True), and the recall result (did it fire, on every run or only some). If
recall is below full, the context was present but did not fire, so a comparison would measure a
supply bug, not a context effect; stop there. State the honest status from the SetupSpec:
B3-metric-definition, B4-schema, and B7-task-scoping are buildable-now; B5-query-patterns and
B6-corrections are partial (toggle and fixture are real, the does-not-recur proof needs a live
run); never present a partial or blocked setup as a pass. Boundary: this skill only proves the
context is staged and cited. Whether it moved the answer is the user's live run, handed to
`/compare`.
