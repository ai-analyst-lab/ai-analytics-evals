"""The comparison run: the core move of the eval tool.

Hold the question, the model, and the data fixed. Run the same question two ways, under
different setups (for example, with a metric definition and without it), and measure the
delta. The setup whose presence collapses a wide spread to one stable number is the context
that moves the answer. The setup that changes nothing was not worth having.

This module is analyst-agnostic: it computes the delta from per-setup runs. Producing the
runs (asking the analyst N times under a setup) is the adapter's job, so the tool can test
any analyst. The math is the shared deterministic stats, so the comparison run and the plain
reliability check never disagree.
"""
import json
from pathlib import Path

from aievals.stats.reliability import compute


def stats_for_runs(runs):
    """Deterministic stats for one setup's list of runs."""
    return compute(runs)


def load_runs(source):
    """Accept a run directory (with runs.json), a runs.json path, or an inline list."""
    if isinstance(source, list):
        return source
    p = Path(source)
    if p.is_dir():
        p = p / "runs.json"
    payload = json.loads(p.read_text())
    return payload.get("runs", payload if isinstance(payload, list) else [])


def comparison_delta(setups):
    """setups: ordered list of {"name", and "runs"(list) or "runs_dir"/"runs_path"}.

    The first setup is the baseline. Returns per-setup stats plus the delta from the
    baseline to each later setup: the change in spread (CV, distinct values), in dictionary
    citation, and in the STABLE / DRIFT verdict, and whether that setup moved the answer.
    """
    rows = []
    for c in setups:
        runs = c["runs"] if "runs" in c else load_runs(c.get("runs_dir") or c.get("runs_path"))
        s = stats_for_runs(runs)
        rows.append({
            "name": c["name"],
            "n": s.get("n"),
            "verdict": s.get("verdict"),
            "cv": s.get("cv"),
            "n_distinct": s.get("n_distinct"),
            "agreement_rate": s.get("agreement_rate"),
            "used_dictionary": s.get("used_dictionary"),
            "distinct_values": s.get("distinct_values"),
        })

    base = rows[0]
    deltas = []
    for r in rows[1:]:
        deltas.append({
            "from": base["name"],
            "to": r["name"],
            "verdict_change": f"{base['verdict']} -> {r['verdict']}",
            "cv_drop": _round(_sub(base["cv"], r["cv"])),
            "distinct_drop": _sub(base["n_distinct"], r["n_distinct"]),
            "agreement_gain": _round(_sub(r["agreement_rate"], base["agreement_rate"])),
            "dictionary_gain": _sub(r["used_dictionary"], base["used_dictionary"]),
            "moves_the_answer": _moves_the_answer(base, r),
        })
    return {"setups": rows, "deltas": deltas}


def _sub(a, b):
    if a is None or b is None:
        return None
    return a - b


def _round(x):
    return round(x, 4) if isinstance(x, (int, float)) else x


def _moves_the_answer(base, other):
    """A setup moves the answer if turning it on took the system from DRIFT to a tighter
    state: the verdict improved, or the spread dropped meaningfully."""
    if base["verdict"] == "DRIFT" and other["verdict"] == "STABLE":
        return True
    cv_drop = _sub(base["cv"], other["cv"])
    if cv_drop is not None and cv_drop > 0.02:
        return True
    if _sub(base["n_distinct"], other["n_distinct"]) and base["n_distinct"] - other["n_distinct"] > 0:
        return True
    return False


def write_report(out_dir, question, result):
    """Write the short readable comparison report plus the machine-readable json."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# Comparison report", "", f"**Question:** {question}", "",
             "## Per setup", "",
             "| Setup | Verdict | Distinct | Agreement | CV | Cited definition |",
             "|---|---|---|---|---|---|"]
    for c in result["setups"]:
        lines.append(
            f"| {c['name']} | {c['verdict']} | {c['n_distinct']} | {c['agreement_rate']} | "
            f"{c['cv']} | {c['used_dictionary']} / {c['n']} |")
    lines += ["", "## Delta from baseline", ""]
    for d in result["deltas"]:
        lines += [
            f"### {d['from']} -> {d['to']}",
            f"- verdict: {d['verdict_change']}",
            f"- CV drop: {d['cv_drop']}",
            f"- distinct values removed: {d['distinct_drop']}",
            f"- definition citations gained: {d['dictionary_gain']} runs",
            f"- this setup moves the answer: {d['moves_the_answer']}",
            "",
        ]
    lines += ["_The delta is computed deterministically from the recorded runs, not asserted. "
              "A setup that moves the answer is one whose presence collapses the drift the question "
              "shows without it. Convergence is stability, not correctness._"]
    (out / "comparison_report.md").write_text("\n".join(lines))
    (out / "comparison.json").write_text(json.dumps({"question": question, **result}, indent=2))
    return out / "comparison_report.md"
