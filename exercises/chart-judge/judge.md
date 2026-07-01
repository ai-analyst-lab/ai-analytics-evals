# Judge (prompt template)

You score one chart against the rubric in RUBRIC.md. Run BLIND: do not read scores.csv before you
score. For each axis in RUBRIC.md:
1. Reason one sentence about the chart against that axis's pass/fail anchors.
2. Return a verdict: pass or fail.

Rules:
- One pass/fail per axis. Never a 1-5.
- A chart's overall verdict is pass only if every axis passes.
- Judge the chart only; do not invent data you cannot see.

After scoring, record it (do not read the file first):
  python3 log_score.py --chart <name>.png --rubric-version <the rubric_version in RUBRIC.md> \
      --verdicts "axis1=pass,axis2=fail,..."
