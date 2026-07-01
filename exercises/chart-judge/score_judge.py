#!/usr/bin/env python3
"""Measure the judge's ALIGNMENT to the golden set. Takes the judge's overall pass/fail per golden
chart and the human gold labels, computes precision/recall/F1, and appends to alignment-scores.csv so
you watch alignment climb as you improve the rubric.

    python3 score_judge.py --rubric-version r5 \
        --judge "chart-01.png=pass,chart-02.png=fail,..."   # judge's overall verdict per golden chart
Gold labels are read from golden/golden-labels.csv (chart,gold_verdict).
"""
import argparse, csv, pathlib, datetime, uuid
HERE = pathlib.Path(__file__).parent
GOLD = HERE / "golden" / "golden-labels.csv"
ALIGN = HERE / "alignment-scores.csv"

def load_gold():
    d = {}
    with open(GOLD) as f:
        for row in csv.DictReader(f):
            d[row["chart"].strip()] = row["gold_verdict"].strip().lower()
    return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rubric-version", default="")
    ap.add_argument("--judge", required=True, help="chart=pass|fail,comma-separated (judge's overall verdict)")
    a = ap.parse_args()
    gold = load_gold()
    judge = {}
    for p in a.judge.split(","):
        if "=" in p:
            c, v = p.split("="); judge[c.strip()] = v.strip().lower()
    charts = sorted(set(judge) & set(gold))
    tp = fp = fn = tn = 0
    for c in charts:
        j, g = judge[c], gold[c]
        if j == "pass" and g == "pass": tp += 1
        elif j == "pass" and g == "fail": fp += 1
        elif j == "fail" and g == "pass": fn += 1
        else: tn += 1
    prec = tp/(tp+fp) if (tp+fp) else float("nan")
    rec = tp/(tp+fn) if (tp+fn) else float("nan")
    f1 = 2*prec*rec/(prec+rec) if (prec+rec) else float("nan")
    print(f"scored {len(charts)} golden charts  TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  precision {prec:.2f}  recall {rec:.2f}  F1 {f1:.2f}")
    run_id = uuid.uuid4().hex[:8]; ts = datetime.datetime.now().isoformat(timespec="seconds")
    new = not ALIGN.exists()
    with open(ALIGN, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["run_id","timestamp","rubric_version","precision","recall","f1","n"])
        w.writerow([run_id, ts, a.rubric_version, f"{prec:.3f}", f"{rec:.3f}", f"{f1:.3f}", len(charts)])
    print(f"  appended to alignment-scores.csv (rubric {a.rubric_version})")

if __name__ == "__main__":
    main()
