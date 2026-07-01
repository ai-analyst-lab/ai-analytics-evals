#!/usr/bin/env python3
"""Append a judge run to scores.csv, one row per axis. Long format so a growing rubric never changes
the schema. Called by the judge after it scores (the judge passes its per-axis verdicts).

    python3 log_score.py --chart chart-v2.png --rubric-version r3 \
        --verdicts "action-title=pass,focus-color=fail,zero-baseline=pass"
"""
import argparse, csv, pathlib, datetime, uuid
HERE = pathlib.Path(__file__).parent
SCORES = HERE / "scores.csv"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chart", required=True)
    ap.add_argument("--rubric-version", default="")
    ap.add_argument("--verdicts", required=True, help="axis=pass|fail,comma-separated")
    a = ap.parse_args()
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    pairs = [p.split("=") for p in a.verdicts.split(",") if "=" in p]
    new = not SCORES.exists()
    with open(SCORES, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["run_id","timestamp","rubric_version","chart","axis","verdict"])
        for axis, verdict in pairs:
            w.writerow([run_id, ts, a.rubric_version, a.chart, axis.strip(), verdict.strip().lower()])
    passed = sum(1 for _, v in pairs if v.strip().lower() == "pass")
    print(f"logged run {run_id}: {a.chart} scored {passed}/{len(pairs)} against rubric {a.rubric_version}")

if __name__ == "__main__":
    main()
