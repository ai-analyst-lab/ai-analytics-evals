"""E1 The method-ranking campaign.

Track B measures one setup at a time. The payoff is ranking which context methods actually move
the answer, across the whole grid. This aggregates the per-setup comparison deltas into a ranking:
which layers are load-bearing versus ceremony. It is the campaign-scale form of the comparison
run, and it runs as a deliberate, sampled, occasional campaign, never on every cohort.

A ranking is only trustworthy under the validity controls: a delta below the noise floor is
reported as "not distinguishable from noise," not as an effect, and the campaign assumes a pinned
model across arms (harness.controls). It resolves the granularity decision (FRAMEWORK_v0 D1) ONLY
when B-granularity has staged the per-metric, single-index, and domain-bundled arms for it to
rank; without those arms there is nothing to rank and the campaign says so rather than claiming a
result. Sampling size is a speed-and-usage choice, not a money one.

Source: BUILD_STATUS W5.1, ABLATION-HARNESS-DEMO, CONTEXT-DECISION-GRID, FRAMEWORK_v0 §11 D1.
"""
from aievals.harness.controls import distinguishable


def rank_methods(setup_deltas, floor):
    """Rank context setups by measured delta, largest first.

    `setup_deltas` is a list of {"setup": key, "delta": <a number, larger means moved the answer
    more>}. `floor` is the noise floor (harness.controls.noise_floor). Each ranked item carries
    whether its delta is distinguishable from noise; sub-noise deltas are ranked last and marked
    not-distinguishable, never presented as a real effect.
    """
    ranked = []
    for d in setup_deltas:
        delta = d.get("delta")
        dist = distinguishable(delta, floor)
        ranked.append({
            "setup": d["setup"],
            "delta": delta,
            "distinguishable": dist,
            "verdict": ("moves the answer" if dist else
                        "not distinguishable from noise" if dist is False else
                        "undetermined (missing delta or floor)"),
        })
    # Distinguishable effects first (by size), then the rest. None deltas sort to the bottom.
    ranked.sort(key=lambda r: (r["distinguishable"] is True, abs(r["delta"]) if r["delta"] is not None else -1),
                reverse=True)
    return ranked


def resolve_granularity(granularity_deltas, floor):
    """Resolve FRAMEWORK_v0 D1 (per-metric vs single-index vs domain-bundled) from staged arms.

    Returns the winning granularity ONLY if B-granularity staged arms to rank; otherwise returns
    a not-resolved result that names the missing dependency, so the campaign never claims to have
    settled D1 when it had nothing to rank.
    """
    arms = list(granularity_deltas or [])
    expected = {"per-metric", "single-index", "domain-bundled"}
    have = {a.get("setup") for a in arms}
    if not expected.issubset(have):
        return {"resolved": False,
                "reason": "B-granularity has not staged all three arms "
                          f"(need {sorted(expected)}, have {sorted(have)}); D1 cannot be resolved",
                "winner": None}
    ranked = rank_methods(arms, floor)
    top = ranked[0]
    if top["distinguishable"] is not True:
        return {"resolved": False,
                "reason": "no granularity arm moved the answer above the noise floor; D1 stays open",
                "winner": None, "ranking": ranked}
    return {"resolved": True, "winner": top["setup"], "ranking": ranked}
