#!/usr/bin/env python3
"""Append one arm's result to directions.csv. Long format, append-only, same pattern as the
chart-judge's scores.csv. Called after an arm answers (the arm runs blind: answer first, log after,
do not read this file first).

    python3 log_direction.py --method before-after --direction no \
        --headline "-10.3% vs prior fortnight" --basis "promo window revenue below the prior equal window"
"""
import argparse, csv, pathlib, datetime, uuid
HERE = pathlib.Path(__file__).parent
LOG = HERE / "directions.csv"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True)
    ap.add_argument("--direction", required=True, choices=["yes", "no", "unclear"])
    ap.add_argument("--headline", default="")
    ap.add_argument("--basis", required=True)
    a = ap.parse_args()
    new = not LOG.exists()
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["run_id", "timestamp", "method", "direction", "headline", "basis"])
        w.writerow([uuid.uuid4().hex[:8], datetime.datetime.now().isoformat(timespec="seconds"),
                    a.method, a.direction, a.headline, a.basis])
    print(f"logged: {a.method} -> {a.direction} ({a.basis})")

if __name__ == "__main__":
    main()
