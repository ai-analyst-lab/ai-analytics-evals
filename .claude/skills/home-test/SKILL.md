---
name: home-test
description: Stage the SAME meaning-only contract from two homes (a repo file and a warehouse table row) and show the meaning is identical, so the home does not change the answer, only the read cost and how governable the definition is. Use when the user says "/home-test", "does it matter where the context lives", "compare repo vs warehouse home", "stage the contract from a table", or wants to see the B-home axis (storage home) tested by hand. The repo arm runs hermetically off the canonical fixture; the warehouse arm reads the same text over a connection the caller supplies.
---

# Skill: Home-test (does WHERE the context lives change the answer)

## Purpose
Show the B-home lesson by hand: take one layer's content (the proven retention contract) and stage
it from two different homes, a repo file and a warehouse table row, with the format held constant
(meaning-only YAML, declarative). If the meaning is identical across homes, the home cannot change
the answer; it only changes the read cost and how governable the definition is. The companion is
`/scorecard` for grading an answer and `/compare` for the live agentic run.

## Invocation
`/home-test` (optionally `--conn <a supplied connection>` for a real warehouse home)

With no connection supplied the demo seeds an in-memory DuckDB with the same contract text, so the
warehouse arm runs hermetically. The live Snowflake arm and the Notion arm are blocked; this skill
says so rather than faking a pass.

## How to run it
Run from `~/projects/ai-analytics-evals`. Populate the setup registry, read the contract from the
repo home, seed and read it from the warehouse home, and compare the two overlays.

```python
from aievals.setups import load_all as _sl
_sl()
from aievals.setups.b_home import repo_home, warehouse_home, notion_home, CONTRACT_FILE
from aievals.setups.base import registry
import duckdb

# Repo arm (BUILT, the baseline): the contract as a declarative file, read by FileReader.
repo = repo_home()
repo_overlay = repo.read_overlays()[0]

# Warehouse arm: seed an in-memory DuckDB with the SAME contract text in a metrics-table row,
# then read it via the WarehouseReader over the supplied connection (the tool holds no credentials).
conn = duckdb.connect(":memory:")
conn.execute("CREATE TABLE metric_contracts (metric VARCHAR, contract_text VARCHAR)")
conn.execute("INSERT INTO metric_contracts VALUES (?, ?)",
             ["retention_rate", CONTRACT_FILE.read_text()])
wh_overlay = warehouse_home(conn=conn).read_overlays()[0]

print("meaning identical across homes:", repo_overlay == wh_overlay)
print("metric means same:",
      repo_overlay["metrics"][0]["means"] == wh_overlay["metrics"][0]["means"])

spec = registry()["B-home"]                # honest status, read from the SetupSpec, not asserted
print("B-home status:", spec.status, "|", spec.blocked_on[:80])

try:                                       # the Notion arm is blocked; show the blocked read
    notion_home().read_overlays()
except RuntimeError as e:
    print("notion arm: BLOCKED -", str(e)[:70])
```

## Present it
Show that the two overlays are equal: the repo file and the warehouse row carry the same meaning, so
the home is the only variable and it does not move the answer. Then name what DOES differ between
homes (the read cost and the governability) and the honest boundary, read from the SetupSpec:
B-home status is `partial`. The live Snowflake arm is blocked (the bootcamp_student role is
read-only and cannot seed a table), and the Notion arm is blocked (no token, no live page-read), so
the in-memory DuckDB stands in for the warehouse mechanism. The full effect (asking the live analyst
N times from each home) is the user's live run, handed to `/compare`.
