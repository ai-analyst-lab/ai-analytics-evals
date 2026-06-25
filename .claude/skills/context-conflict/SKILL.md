---
name: context-conflict
description: Show the L1-vs-L3 precedence rule when a company glossary term and an area metric contract disagree. Use when the user says "/context-conflict", "what wins when the glossary and the contract disagree", "show the source-authority ladder", "does L1 or L3 win on a conflict", or wants to see that an area-level contract (L3) beats a company-level term (L1) and the conflict is flagged, never silently resolved in favor of the company doc. Stages a conflicting pair and runs the resolver.
---

# Skill: Context-conflict (the L1-vs-L3 precedence rule)

## Purpose
Show what happens when two layers of context disagree about the same term. A company-wide glossary
(L1) and an area owner's metric contract (L3) can define "active customer" differently. The rule
(FRAMEWORK_v0 section 5.2) is that the area contract wins on source authority and the disagreement
is surfaced loudly, so the answer never quietly inherits a stale company definition. The companion
skills are `/check` (one grader) and `/scorecard` (the whole card).

## Invocation
`/context-conflict` (optionally name the term, e.g. "for active customer")

## How to run it
Run from `~/projects/ai-analytics-evals`. Import the glossary setup, stage a conflicting L1/L3 pair
for the same term, confirm they really disagree, then walk the ladder with resolve_conflict.

```python
from aievals.setups import b1c_company_glossary as g

# A company-level (L1) term and an area-level (L3) contract that define the same term differently.
l1 = {"term": "active customer", "means": "any account with a login in the last 90 days",
      "grain": "account", "layer": "L1", "scope": "company-wide"}
l3 = {"term": "active customer", "means": "an account with a purchase in the last 30 days",
      "grain": "account", "layer": "L3", "scope": "area"}

assert g.definitions_disagree(l1, l3), "the staged pair should actually conflict"
res = g.resolve_conflict(l1, l3)
print("flagged_conflict:", res["flagged_conflict"])
print("winner_layer:   ", res["winner_layer"])
print("decided_by:     ", res["decided_by"])
print("winner means:   ", res["winner"]["means"])
```

The pair above ties on recency (neither carries a date), so the ladder falls to the source-authority
rung, where area L3 outranks company L1. To show a different rung deciding, add `last_verified` dates
(recency rung) or `confidence` grades A/B/C/F (confidence rung) and watch `decided_by` change.

## Present it
Read three fields. `flagged_conflict` is always True, so the disagreement is surfaced, never hidden.
`winner_layer` is L3, so the area contract wins. `decided_by` names the rung that settled it
(here source-authority, because area owners know their domain better than any company-wide doc).
The boundary: when every rung ties, the resolver does not invent a tie-break; it returns winner None
with `decided_by="human"` and escalates. The staging here is deterministic. Whether a live analyst
actually honors the L3 winner across N runs is the user's live run via `/reliability` or `/compare`.
