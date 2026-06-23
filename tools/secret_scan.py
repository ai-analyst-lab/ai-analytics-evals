#!/usr/bin/env python3
"""Secret scan: the gate that runs before any public push.

Open everything is only safe if no credential ever reaches the public side. This scans the
files git would actually ship (tracked files) for credential patterns, private keys, and any
tracked or un-ignored .env, and exits non-zero if it finds anything. It redacts what it finds
so the scan output itself never leaks a secret.

Usage:
    python3 tools/secret_scan.py [repo_root]      # defaults to this repo

Exit code 0 = clean, 1 = findings (or a tracked/un-ignored .env).
"""
import re
import subprocess
import sys
from pathlib import Path

# Patterns that should never appear in a tracked file. Each is (label, compiled regex).
# We flag credential KEYS assigned a LITERAL value (a quoted string, or a bare token in a
# .env line). Code that READS a credential (password = os.environ.get(...)) has no literal
# value and is not flagged. The key may carry a prefix (DB_PASSWORD, MY_API_KEY).
PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("password literal", re.compile(r"(?i)[a-z0-9_]*(?:password|passwd|pwd)\s*[=:]\s*(['\"])([^'\"\s]{6,})\1")),
    ("secret literal", re.compile(r"(?i)[a-z0-9_]*(?:secret|api[_-]?key|token|access[_-]?key)\s*[=:]\s*(['\"])([^'\"\s]{8,})\1")),
    ("snowflake password (.env style)", re.compile(r"SNOWFLAKE_PASSWORD\s*=\s*([^\s'\"$]{6,})")),
]

# Files where a credential-shaped string is expected and not a leak (docs that name the
# variable, example templates, this scanner and its test). Matched by path suffix.
ALLOWLIST_SUFFIXES = (
    ".example",          # any *.example template file (placeholders, not real values)
    "tools/secret_scan.py",
    "tools/test_secret_scan.py",
    "DATA-GOVERNANCE.md",
)

# A matched value that is a placeholder, not a literal secret, is fine: a $ENV reference
# (e.g. password: $SNOWFLAKE_PASSWORD in a manifest), a <template>, or an obvious stub.
PLACEHOLDER = ("$", "<", "{", "your_", "xxx", "example", "changeme", "redacted")


def _git_tracked_files(root):
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files"],
                             capture_output=True, text=True, check=True).stdout
        return [root / line for line in out.splitlines() if line.strip()]
    except Exception:
        # Not a git repo: fall back to all files except the usual noise.
        skip = {".git", "node_modules", "__pycache__", ".venv"}
        return [p for p in root.rglob("*") if p.is_file() and not (skip & set(p.parts))]


def _redact(text):
    return text[:8] + "...[redacted]" if len(text) > 8 else "[redacted]"


def scan_repo(root):
    """Return a list of findings: dicts with file, line, label, redacted match."""
    root = Path(root)
    findings = []

    tracked = _git_tracked_files(root)
    rels = {str(p.relative_to(root)) for p in tracked}

    # 1. A tracked .env (or any *.env that is not an example) is an immediate fail.
    for rel in rels:
        name = rel.rsplit("/", 1)[-1]
        if name == ".env" or (name.endswith(".env") and not name.endswith(".env.example")):
            findings.append({"file": rel, "line": 0, "label": "tracked .env file", "match": "[file]"})

    # 2. Scan tracked text files for credential patterns.
    for p in tracked:
        rel = str(p.relative_to(root))
        if any(rel.endswith(s) for s in ALLOWLIST_SUFFIXES):
            continue
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for label, rx in PATTERNS:
                m = rx.search(line)
                if not m:
                    continue
                matched = m.group(0)
                # A $ENV reference, a <template>, or an obvious stub is a placeholder, not a leak.
                if any(ph in matched.lower() for ph in PLACEHOLDER):
                    continue
                findings.append({"file": rel, "line": i, "label": label, "match": _redact(matched)})

    return findings


def check_env_ignored(root):
    """Return a finding if a .env exists on disk but is not gitignored."""
    root = Path(root)
    env = root / ".env"
    if not env.exists():
        return None
    try:
        rc = subprocess.run(["git", "-C", str(root), "check-ignore", ".env"],
                            capture_output=True).returncode
        if rc != 0:
            return {"file": ".env", "line": 0, "label": ".env exists but is NOT gitignored", "match": "[file]"}
    except Exception:
        return None
    return None


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    findings = scan_repo(root)
    ig = check_env_ignored(root)
    if ig:
        findings.append(ig)
    if findings:
        print(f"SECRET SCAN FAILED on {root}: {len(findings)} finding(s)")
        for f in findings:
            loc = f["file"] + (f":{f['line']}" if f["line"] else "")
            print(f"  {loc}  [{f['label']}]  {f['match']}")
        sys.exit(1)
    print(f"secret scan clean: {root}")
    sys.exit(0)


if __name__ == "__main__":
    main()
