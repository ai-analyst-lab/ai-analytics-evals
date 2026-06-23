"""B1c Company / org glossary (canonical layer L1), plus the L1-vs-L3 precedence resolver.

Two things live here because they are two halves of one idea: the company-wide glossary is a real
context layer you can stage on or off, and the moment you stage it you inherit the question of what
happens when it DISAGREES with an area owner's contract. The org glossary is the small, resident,
company-level layer (org-wide term definitions, slow to change). Staging it is buildable now, the
same file-overlay mechanism the L3 metric contract uses.

The precedence resolver is the load-bearing part. Sravya's rule (FRAMEWORK_v0 section 5, verbatim)
is that area-level context (L3) ALWAYS beats company-level context (L1) on conflict, because area
owners know their domain better than any company-wide document. The conflict tie-break is a declared
hierarchy, surfaced loudly and never silently picked: recency, then source authority (area L3 over
company L1), then confidence (the DRI grade A over B over C over F), then specificity, then a human.
resolve_conflict walks that ladder in order and returns the winner together with flagged_conflict
set True, so a company term and an area contract that disagree can never resolve quietly in favor of
the company doc. The DRI grade mentioned inside source authority in the source text is evaluated
here at the confidence rung, so each rung reads one distinct signal and nothing is double counted.

Source: C-store.md (section 1.2, the nested store and the area-beats-company precedence; section 3.2
conflict resolution) and FRAMEWORK_v0 section 5.2 (append-with-supersession conflict tie-break).
"""
from datetime import date, datetime

from aievals.harness.setups import Setup
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup

# The default company glossary fixture (an L1 overlay file, not the whole fixtures dir, so the L3
# retention contract that also lives there is not composed into the company layer by accident).
DEFAULT_GLOSSARY = FIXTURES / "company_glossary.yaml"


# ---- the setup: stage the org glossary on or off -------------------------------------------

def build(glossary=None, **ctx):
    """Return the glossary-on arm. `glossary` is the path to the company glossary overlay (a file or
    a directory of *.yaml), analyst-side when testing a real analyst. It defaults to our canonical
    teaching fixture so the setup runs hermetically. The glossary-off arm is `baseline()`."""
    spec = str(glossary) if glossary is not None else str(DEFAULT_GLOSSARY)
    return Setup(name="with-company-glossary", layer="L1", reader="file", spec=spec)


def baseline():
    """The glossary-off arm: the bare baseline the glossary-on arm is compared against."""
    return Setup(name="no-glossary", layer=None, reader="file", spec=None)


# ---- the L1-vs-L3 precedence resolver ------------------------------------------------------

# Layer ranks: a larger L-number sits nearer the work (more area-specific), so it carries more
# source authority. Area (L3, L4) outranks company (L1, L2), per Sravya's precedence rule.
_LAYER_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5, "L6": 6}
# DRI grade, the confidence rung. A is owner-reviewed and query-tested, F is known-wrong.
_GRADE_RANK = {"A": 4, "B": 3, "C": 2, "F": 1}
# Scope specificity: a dataset/area-scoped belief is more specific than a company-wide one.
_SCOPE_RANK = {"dataset": 4, "area": 3, "team": 2, "company-wide": 1, "company": 1, "org": 1}


def _recency(d):
    """Parse a comparable recency signal (last_verified, else valid_from). Returns a date or None
    when no parseable date is present."""
    v = d.get("last_verified", d.get("valid_from"))
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def _layer_rank(d, default):
    """Source-authority rank from the def's declared layer, falling back to its role (the company
    candidate or the area candidate) when the layer is not stated on the dict."""
    layer = d.get("layer")
    if layer in _LAYER_RANK:
        return _LAYER_RANK[layer]
    return default


def _grade_rank(d):
    g = (d.get("confidence") or d.get("dri_grade") or d.get("grade") or "").upper()
    return _GRADE_RANK.get(g, 0)


def _specificity_rank(d):
    s = d.get("specificity")
    if isinstance(s, (int, float)):
        return float(s)
    return _SCOPE_RANK.get((d.get("scope") or "").lower(), 0)


def _layer_of(d, default):
    layer = d.get("layer")
    return layer if layer in _LAYER_RANK else default


# The ladder, in declared order. Each rung reads the two defs and returns "l3", "l1", or None
# (None means the rung does not decide and we fall to the next one). l1_def is the company
# candidate, l3_def is the area candidate.
def _rung_recency(l1, l3):
    r1, r3 = _recency(l1), _recency(l3)
    if r1 is None or r3 is None or r1 == r3:
        return None
    return "l3" if r3 > r1 else "l1"


def _rung_source_authority(l1, l3):
    a1 = _layer_rank(l1, default=_LAYER_RANK["L1"])
    a3 = _layer_rank(l3, default=_LAYER_RANK["L3"])
    if a3 == a1:
        return None
    return "l3" if a3 > a1 else "l1"


def _rung_confidence(l1, l3):
    c1, c3 = _grade_rank(l1), _grade_rank(l3)
    if c1 == c3:
        return None
    return "l3" if c3 > c1 else "l1"


def _rung_specificity(l1, l3):
    s1, s3 = _specificity_rank(l1), _specificity_rank(l3)
    if s1 == s3:
        return None
    return "l3" if s3 > s1 else "l1"


_LADDER = (
    ("recency", _rung_recency),
    ("source-authority", _rung_source_authority),
    ("confidence", _rung_confidence),
    ("specificity", _rung_specificity),
)


def resolve_conflict(l1_def, l3_def):
    """Resolve a disagreement between a company-level (L1) term and an area-level (L3) contract.

    Walks the declared ladder (recency, then source authority where area L3 beats company L1, then
    confidence, then specificity) and stops at the first rung that decides. When every rung ties,
    the winner is None and the conflict escalates to a human (decided_by="human"); the resolver
    never invents a tie-break. flagged_conflict is always True, because this is only ever called on
    a real disagreement and the contract is that such a conflict is surfaced, never silently picked
    in favor of the company doc.

    Returns a dict: {winner, winner_layer, decided_by, flagged_conflict}. `winner` is the winning
    def (or None when escalated to a human).
    """
    for name, rung in _LADDER:
        choice = rung(l1_def, l3_def)
        if choice is not None:
            winner = l3_def if choice == "l3" else l1_def
            default_layer = "L3" if choice == "l3" else "L1"
            return {
                "winner": winner,
                "winner_layer": _layer_of(winner, default_layer),
                "decided_by": name,
                "flagged_conflict": True,
            }
    return {
        "winner": None,
        "winner_layer": None,
        "decided_by": "human",
        "flagged_conflict": True,
    }


def definitions_disagree(a, b):
    """A light check that two definitions of the same term actually conflict, used to decide whether
    resolve_conflict should even run. Compares the meaning and the grain, normalized for whitespace.
    """
    def norm(x):
        return " ".join((x or "").split()).strip().lower()
    same_term = norm(a.get("term", "")) == norm(b.get("term", ""))
    same_meaning = norm(a.get("means", "")) == norm(b.get("means", "")) and \
        norm(a.get("grain", "")) == norm(b.get("grain", ""))
    return same_term and not same_meaning


register_setup(SetupSpec(
    key="B1c-company-glossary",
    layer="L1",
    status="buildable-now",
    summary="Stage the org glossary on or off; plus the L1-vs-L3 resolver where area L3 beats "
            "company L1 on conflict and the conflict is always flagged.",
    source="C-store.md, FRAMEWORK_v0 §5.2",
    build=build,
))
