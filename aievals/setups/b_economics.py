"""B-economics (cross-cutting, no single layer): economics and the resident token footprint.

The context chapter (C-economics) makes one claim load-bearing: more context is not free even
inside the window, and past a point it is actively worse, the relevant tokens get buried among
distractors and quality drops. That claim only earns its place if it is measurable on our own
runs rather than asserted from the public studies. So this unit is a MEASUREMENT, not a
stageable overlay. There is nothing to toggle on or off here; the other B units stage layers,
and each of their runs records a RunMeta (model, seconds, tokens, cost). This unit reads those
RunMetas back and reports the resident token footprint per setup and the delta between the lean
arm and the heavy arm, so "loading more is not better past a point" becomes a number you can put
next to a reliability or known-answer result.

It deliberately measures footprint only. It does not claim that a larger footprint is worse on
its own; that conclusion comes from reading this footprint next to a quality signal (A1
reliability, A2 known-answer). Keeping the two separate is the honest split: footprint is a cost
fact, quality is a separate fact, and the rot story is the relationship between them, which the
caller composes. Because there is no overlay to build, the SetupSpec carries build=None even
though the measurement itself is buildable now; the summary says so out loud.

The resident footprint is read from RunMeta.input_tokens, the tokens resident in the window when
the run was made (the context plus the question). RunMeta is the only place those counts live, so
input_tokens is the proxy this report uses for "what was in the window". Output tokens and the
computed cost are carried alongside for context, never folded into the footprint.
"""
from aievals.harness.run_meta import RunMeta
from aievals.setups.base import SetupSpec, register_setup


def _meta_field(meta, field):
    """Read a field from a RunMeta dataclass or its as_dict() form, so callers can pass either."""
    if isinstance(meta, dict):
        return meta.get(field)
    return getattr(meta, field, None)


def footprint_report(setups_with_meta):
    """Measure the resident token footprint per setup and the delta across them.

    `setups_with_meta` is a list of {"name": str, "meta": RunMeta} (meta may be a RunMeta or its
    as_dict() form). Returns:

      {
        "per_setup": [{"name", "footprint_tokens", "output_tokens", "cost_usd"}, ...],
        "delta": None | {
            "leanest": name, "heaviest": name,
            "leanest_tokens": int, "heaviest_tokens": int,
            "footprint_delta": int,   # heaviest minus leanest, never negative
            "detail": str,            # states this is footprint, not a quality verdict
        },
      }

    `per_setup` preserves input order. `delta` is None for fewer than two setups (nothing to
    compare). The footprint is RunMeta.input_tokens, the tokens resident in the window for that
    run; it is a cost measurement, not a quality verdict. Reading it next to a reliability or
    known-answer result is what shows whether more context bought anything.
    """
    per_setup = []
    for item in setups_with_meta:
        meta = item["meta"]
        footprint = _meta_field(meta, "input_tokens")
        per_setup.append({
            "name": item["name"],
            "footprint_tokens": footprint if footprint is not None else 0,
            "output_tokens": _meta_field(meta, "output_tokens"),
            "cost_usd": _meta_field(meta, "cost_usd"),
        })

    delta = None
    if len(per_setup) >= 2:
        ordered = sorted(per_setup, key=lambda r: r["footprint_tokens"])
        leanest, heaviest = ordered[0], ordered[-1]
        gap = heaviest["footprint_tokens"] - leanest["footprint_tokens"]
        delta = {
            "leanest": leanest["name"],
            "heaviest": heaviest["name"],
            "leanest_tokens": leanest["footprint_tokens"],
            "heaviest_tokens": heaviest["footprint_tokens"],
            "footprint_delta": gap,
            "detail": (f"{heaviest['name']} kept {gap} more resident token(s) than "
                       f"{leanest['name']}. This is footprint (cost), not a quality verdict; "
                       "read it next to a reliability or known-answer result to see whether the "
                       "heavier context bought anything."),
        }
    return {"per_setup": per_setup, "delta": delta}


register_setup(SetupSpec(
    key="B-economics",
    layer=None,                       # cross-cutting: a measurement over every setup's run_meta
    status="buildable-now",
    summary=("A measurement, not a stageable overlay: footprint_report() reads each setup's "
             "RunMeta token counts and reports the resident footprint per setup plus the delta, "
             "so 'more context is not better past a point' becomes a number. build=None because "
             "there is no layer to toggle; the report runs over runs the other B units produce."),
    blocked_on=None,
    source="C-economics.md",
    build=None,                       # nothing to stage; this unit measures, it does not toggle
))
