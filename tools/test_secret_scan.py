#!/usr/bin/env python3
"""Tests for the secret scan gate. Run: python3 tools/test_secret_scan.py"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import secret_scan

passed = failed = 0
def check(name, cond):
    global passed, failed
    if cond: passed += 1; print(f"  ok   {name}")
    else: failed += 1; print(f"  FAIL {name}")


def _git_init(d):
    subprocess.run(["git", "init", "-q", d], check=True)


def test_catches_planted_secret():
    with tempfile.TemporaryDirectory() as d:
        _git_init(d)
        (Path(d) / "config.py").write_text('DB_PASSWORD = "hunter2supersecret"\n')
        subprocess.run(["git", "-C", d, "add", "-A"], check=True)
        findings = secret_scan.scan_repo(d)
        check("catches a planted password literal", any("password" in f["label"] for f in findings))
        check("redacts the secret in output", all("hunter2supersecret" not in f["match"] for f in findings))


def test_catches_tracked_env():
    with tempfile.TemporaryDirectory() as d:
        _git_init(d)
        (Path(d) / ".env").write_text("SNOWFLAKE_PASSWORD=DontDropTables26\n")
        subprocess.run(["git", "-C", d, "add", "-f", ".env"], check=True)
        findings = secret_scan.scan_repo(d)
        check("catches a tracked .env", any("env" in f["label"] for f in findings))


def test_clean_repo_passes():
    with tempfile.TemporaryDirectory() as d:
        _git_init(d)
        (Path(d) / "ok.py").write_text("x = 1\nprint('hello')\n")
        subprocess.run(["git", "-C", d, "add", "-A"], check=True)
        check("clean repo has no findings", secret_scan.scan_repo(d) == [])


def test_env_placeholder_is_not_a_leak():
    with tempfile.TemporaryDirectory() as d:
        _git_init(d)
        (Path(d) / "manifest.yaml").write_text("connection:\n  password: $SNOWFLAKE_PASSWORD\n")
        subprocess.run(["git", "-C", d, "add", "-A"], check=True)
        check("a $ENV placeholder is not flagged", secret_scan.scan_repo(d) == [])


if __name__ == "__main__":
    print("test_secret_scan:")
    test_catches_planted_secret()
    test_catches_tracked_env()
    test_clean_repo_passes()
    test_env_placeholder_is_not_a_leak()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
