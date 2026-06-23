"""Deterministic reliability statistics over N runs of one question.

This is the one source of the math, shared by the reliability check and the comparison
run, so they can never disagree. Given a list of runs, each a dict with a `headline` (the
number it reported) and a `definition_source` (whether it cited a defined metric), it
computes the spread: distinct values, variance, agreement rate, dictionary citations, and
a plain STABLE / DRIFT verdict. The numbers are computed here, never estimated by a model.
"""
import re
import statistics
from collections import Counter

# A run's spread counts as converged (STABLE) when every reading rounds to the same value
# or the relative range is within this fraction of the mean.
CONVERGENCE_REL_RANGE = 0.02


def parse_number(headline):
    """Pull the leading numeric value out of a headline like '25.3%', '$3.15M', '1,409'."""
    if headline is None:
        return None
    text = str(headline).replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    value = float(m.group())
    suffix = text[m.end():m.end() + 1].lower()
    if suffix == "k":
        value *= 1e3
    elif suffix == "m":
        value *= 1e6
    elif suffix == "b":
        value *= 1e9
    return value


def compute(runs):
    """Deterministic stats for one condition's list of runs."""
    n = len(runs)
    headlines = [r.get("headline") for r in runs]
    nums = [v for v in (parse_number(h) for h in headlines) if v is not None]
    stats = {"n": n, "n_numeric": len(nums), "headlines": headlines}

    if nums:
        mean = statistics.fmean(nums)
        sd = statistics.pstdev(nums) if len(nums) > 1 else 0.0
        rounded = [round(v, 4) for v in nums]
        counts = Counter(rounded)
        _, modal_count = counts.most_common(1)[0]
        rel_range = (max(nums) - min(nums)) / abs(mean) if mean else (0.0 if len(set(rounded)) == 1 else 1.0)
        converged = len(set(rounded)) == 1 or rel_range <= CONVERGENCE_REL_RANGE
        stats.update({
            "mean": round(mean, 4),
            "stdev": round(sd, 4),
            "cv": round(sd / mean, 4) if mean else None,   # coefficient of variation
            "min": min(nums),
            "max": max(nums),
            "range": round(max(nums) - min(nums), 4),
            "rel_range": round(rel_range, 4),
            "distinct_values": sorted(set(rounded)),
            "n_distinct": len(set(rounded)),
            "agreements": modal_count,            # runs sharing the most common value
            "differences": n - modal_count,
            "agreement_rate": round(modal_count / n, 3),
            "verdict": "STABLE" if converged else "DRIFT",
        })
    else:
        stats["verdict"] = "UNKNOWN"   # no parseable numbers

    sources = [str(r.get("definition_source") or "").strip().lower() for r in runs]
    stats["used_dictionary"] = sum(1 for s in sources if "dictionary" in s)
    return stats
