---
name: granularity-test
description: Stage the same governed retention definition three structural ways (per-metric in a per-area index, a single flat index, domain-bundled on demand), holding meaning fixed, so the campaign has arms to rank for open decision D1. Use when the user says "/granularity-test", "stage the granularity arms", "build the three structural forms", "set up D1 for the campaign", or wants to see how the metric-definition layer differs by structure alone. This skill produces the arms; the ranking is /rank.
---

# Skill: Granularity test (stage the three structural arms)

## Purpose
Menu C of the context grid leaves one decision open (D1): when the SAME governed definition is
stored, should it live as one contract per metric inside a per-area index, as a single flat index of
all metrics, or domain-bundled and loaded on demand? The grid says teach all three and let the
ablation harness decide. A campaign can only rank options something has actually staged. This skill
stages them. It rewrites the canonical retention contract into the three structural forms while
holding meaning byte-identical (same numerator, denominator, window, filters), so only the file
structure varies. It produces the arms; the ranking is `/rank` (E1), not this skill.

## Invocation
`/granularity-test` (uses the bundled retention contract)

To stage from your own contract, pass `source_contract=<path>`. To control where the forms are
written, pass `staging_dir=<path>`; omitting it creates a hermetic temp directory.

## How to run it
Run from `~/projects/ai-analytics-evals`. Populate the setup registry, then call `build()` on the
B-granularity setup, which returns the three Setups the comparison run toggles, in order.

```python
from aievals.setups import load_all as _sl
from aievals.setups import b_granularity as bg
from aievals.setups.base import registry as setup_registry
_sl()

spec = setup_registry()["B-granularity"]
print("status:", spec.status, "| blocked_on:", spec.blocked_on)

arms = bg.build()  # defaults to the bundled retention contract, hermetic temp staging
for s in arms:
    kind = "list (on-demand load)" if isinstance(s.spec, list) else (
        "directory (reader globs)" if "." not in s.spec.rsplit("/", 1)[-1] else "single file")
    print(f"{s.name} | layer={s.layer} | reader={s.reader} | {kind}")
```

`build()` reads the meaning from `aievals/setups/fixtures/retention_contract.yaml` (the one source
all three forms are rewritten from, which is how meaning is held fixed) and writes the structural
forms to a temp dir. No result number is read or written: the contract carries none and the
structural rewrite adds none. The figure is computed by the analyst at run time, never baked in.

## Show it
Read the three arm names and how they differ on disk: `per-metric-in-area-index` is a DIRECTORY of
one file per metric (the reader globs it), `single-flat-index` is a single FILE, and
`domain-bundled-on-demand` is an explicit LIST of bundle files (the on-demand load). All three sit at
layer L3 (the metric-definition layer is held fixed) so only granularity varies, which is exactly
what the campaign needs to rank for D1. The boundary: this is staging only. It does not decide which
granularity wins. That ranking is E1's job and needs the campaign run (`/rank`), which a person runs
against the live analyst. Status is buildable-now (read it off the SetupSpec above); if it ever
reports otherwise, do not present the arms as ready.
