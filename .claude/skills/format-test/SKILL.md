---
name: format-test
description: Stage the SAME meaning-only retention contract three ways (structured YAML, prose Markdown, executable SQL), holding meaning fixed, and show the three forms differ while carrying no result number. Use when the user says "/format-test", "stage the retention contract three ways", "show the format menu", "does prose drift more than structured", or wants to see the B-format setup before running the drift comparison. The deterministic part proves the three forms exist, differ, and smuggle no answer; the drift delta across formats is a live run handed to /compare.
---

# Skill: Format-test (one meaning, three formats)

## Purpose
Make the format claim testable instead of asserted: the most common silent-drift source in analytics
is putting a definition in prose. This skill stages one retention meaning in three formats (structured
YAML cited by name, prose Markdown the agent re-reads, executable SQL computed by name), holding the
meaning fixed so format is the only variable. The deterministic part shows the three forms exist,
differ, and carry no result number. The companion is `/compare`, which runs the live drift delta.

## Invocation
`/format-test` (no arguments; it stages the bundled fixtures). To point at an analyst-side fixtures
dir laid out the same way, pass `fixtures_dir=` to `build()`.

## How to run it
Run from `~/projects/ai-analytics-evals`. Populate the registry, read B-format's honest status,
build the three arms, and check each staged form carries no answer.

```python
from aievals.setups import load_all as _sl, registry
from aievals.setups import b_format as bf
_sl()
spec = registry()["B-format"]
print("setup", spec.key, "| status:", spec.status, "| blocked_on:", spec.blocked_on)

arms = bf.build()                              # three format forms of the SAME retention meaning
MEASURED = ("55.4", "33.2", "84.8", "75.2")    # figures live runs produced; none belongs in a form
for arm in arms:
    text = "".join(str(ov) for ov in arm.read_overlays())
    has_result = ("%" in text) or any(a in text for a in MEASURED)
    print(f"{arm.name:15} reader={arm.reader:12} carries_result_number={has_result}")

distinct = len({a.spec for a in arms}) == 3 and len({a.reader for a in arms}) > 1
any_result = any(("%" in "".join(str(o) for o in a.read_overlays())) for a in arms)
print("three forms differ:", distinct, "| any result number:", any_result)
```

## Present it
Show the setup key and its status from the SetupSpec (it is buildable-now: pure staging over the
source-reader, no new infrastructure). Then show the three arm names (structured-yaml, prose-markdown,
executable-sql), that they ride distinct readers and distinct files (so the three forms genuinely
differ), and that `carries_result_number` is False on every arm (a metric is defined by meaning, the
figure is computed from the data each run). The boundary: this is the deterministic half only. The
drift delta (does prose drift more than structured on the same question?) needs live runs of the
analyst per arm, so hand that to `/compare` in `~/projects/ai-analyst-plus` as the user's live run.
Convergence there is stability, not correctness, so a stable wrong answer is still a flag.
