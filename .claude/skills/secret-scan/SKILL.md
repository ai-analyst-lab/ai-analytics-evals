---
name: secret-scan
description: Scan a repo for committed credentials before any public push, and fail on the first finding. Use when the user says "/secret-scan", "scan for secrets", "is this safe to push public", "check for leaked credentials", "run the pre-push gate", or wants to know whether tracked files carry a key, password, private key, or a tracked .env. Findings are shown redacted so the scan output itself never leaks a secret; a clean repo reports zero findings.
---

# Skill: Secret scan (the pre-push gate)

## Purpose
Open everything is only safe if no credential ever reaches the public side. This is the gate that
fails on any committed credential before a public push. It scans the files git would actually ship
(tracked files) for credential patterns, private keys, and any tracked or un-ignored `.env`, and
reports each finding redacted. It is deterministic and can scan any repo by path, not just this one.

## Invocation
`/secret-scan` (scans this repo) or `/secret-scan <repo-path>` (scans any repo).

## How to run it
Run from `~/projects/ai-analytics-evals`. The scanner lives in `tools/secret_scan.py`; point
`scan_repo` at the repo path you want to gate (default is this repo), and also run the on-disk
`.env`-not-ignored check, which `scan_repo` cannot see from tracked files alone.

```python
from pathlib import Path
from tools.secret_scan import scan_repo, check_env_ignored

REPO = str(Path("~/projects/ai-analytics-evals").expanduser())  # any repo path works
findings = scan_repo(REPO)
ig = check_env_ignored(REPO)
if ig:
    findings.append(ig)

if findings:
    print(f"SECRET SCAN FAILED on {REPO}: {len(findings)} finding(s)")
    for f in findings:
        loc = f["file"] + (f":{f['line']}" if f["line"] else "")
        print(f"  {loc}  [{f['label']}]  {f['match']}")  # match is already redacted
else:
    print(f"secret scan clean: {REPO}")
```

## Present it
Report the repo path and the verdict: clean (zero findings, safe to push) or failed with the count.
For each finding show only `file:line`, the label (private key block, password literal, secret
literal, aws access key id, snowflake password, or tracked .env), and the redacted match. Never
print the raw secret; the scanner already truncates and redacts it for you.

Boundary: a clean result means no credential matched the known patterns and no `.env` is tracked
or un-ignored. It is a pattern gate, not a proof of safety, so a novel secret shape or a secret
hidden in an allowlisted file (`*.example`, the scanner and its test, `DATA-GOVERNANCE.md`) can
still slip through. Treat clean as "the gate passed", not "nothing secret could ever exist here".
This run is deterministic: the same tracked tree gives the same findings every time.
