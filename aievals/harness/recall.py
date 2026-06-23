"""B-recall: the cheap context-recall precheck (the leading indicator).

Before paying for a full with-and-without comparison, check whether the answer even CITED the
toggled context. Recall under 100% means the context was present but did not fire: a retrieval
miss, a supply bug, not a model bug. This is the cheap gate that nominates which setups are
worth a full comparison run, so runs are not spent on a context the analyst never read.

This reads the citation the analyst emits (the W0.3 receipts substrate: definition_source on
each run block). It cannot read a citation the analyst does not emit, so emission is the hard
dependency, not just staging.
"""


def context_recall(runs, marker="dictionary", citation_keys=("definition_source", "citations")):
    """Of N runs under a staged context, how many cited it?

    `marker` is the substring that marks a citation of the toggled context (for a metric
    definition, "dictionary"). Returns the count, the recall fraction, and whether the context
    fired at all and fired on every run.
    """
    n = len(runs)
    cited = 0
    for r in runs:
        text = " ".join(str(r.get(k) or "") for k in citation_keys).lower()
        if marker.lower() in text:
            cited += 1
    recall = (cited / n) if n else 0.0
    return {
        "n": n,
        "cited": cited,
        "recall": round(recall, 3),
        "fired": cited > 0,
        "full_recall": n > 0 and cited == n,
    }


def should_run_comparison(recall_result, threshold=1.0):
    """The gate: a full comparison is worth running only if recall meets the threshold. Below it
    the finding would be a supply bug, not a context effect, so the comparison is not nominated.
    Default threshold is full recall: the context must fire on every run before we spend a
    comparison measuring what it did."""
    if not recall_result.get("fired"):
        return False
    return recall_result.get("recall", 0.0) >= threshold
