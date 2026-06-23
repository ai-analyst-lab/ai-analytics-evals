"""A3 Provenance (family: inspection).

Inspect that the answer carries its receipt. A provenance footer does not make an answer
correct, it makes it auditable: it is the one trust signal you can ship with zero ground truth,
because every check here is "is the field there, and is it well-formed?", objective inspection
with no annotator and no answer key. That is why this grader lives in the inspection family and
leans on a presence truth basis, never a correctness score over a regime it does not own.

V-provenance defines the canonical footer as FIVE fields: Source-tier, Confidence, Reviewed,
Freshness, Owner. The footer only PARTIALLY exists today. BUILD_STATUS W0.3 records an honest
gap: the analyst's glance footer (provenance_assembler.build_data_stamp) emits the object it
read, a freshness date, and a confidence value, but it does NOT carry an explicit Source-tier or
an Owner, and it has no validated-definition pointer. So A3 is scoped to what the analyst
actually emits today (source/object, freshness, confidence) and grades presence and
well-formedness of those. The remaining fields (explicit Source-tier, Owner, the
validated-definition pointer) are carried as BLOCKED on the W0.3 footer gap, listed in the
result as not-yet-checkable so they are never silently passed. A3 expands to the full five only
when W0.3 adds them and W4.2 pins the required fields.

The grader holds no data and no path. It reads output["footer"], a dict the analyst attaches
after the answer is finalized. Source: V-provenance.md, BUILD_STATUS W0.3.
"""
import re

from aievals.graders.base import Grader, register

# An ISO date, the shape freshness takes (MAX(date) over the rows actually read).
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

# Confidence is a tier, never a free-typed sentence (V-provenance §3). These are the tokens a
# well-formed confidence field may carry; the green/yellow/red tiers plus the common synonyms.
CONFIDENCE_TIERS = ("green", "yellow", "red", "high", "medium", "low")

# The fields the analyst emits today, each with the footer keys that may carry it. A field is
# present if any of its aliases is in the footer with a non-empty value.
REQUIRED_NOW = (
    ("source", ("source", "object")),
    ("freshness", ("freshness",)),
    ("confidence", ("confidence",)),
)

# The fields V-provenance names but the W0.3 footer does not yet emit. Carried as blocked, with
# the reason, so the result lists them as not-yet-checkable rather than passing them by silence.
BLOCKED_FIELDS = {
    "source_tier": "explicit Source-tier (semantic layer > governed > raw) not emitted by "
                   "build_data_stamp; W0.3 footer gap",
    "owner": "Owner (owning-team) field not in the glance footer; W0.3 footer gap",
    "validated_definition": "validated-definition pointer not emitted; W0.3 footer gap, "
                            "pinned by W4.2",
}

# A single blocked_on line summarizing the gap, attached to every result so the blocked fields
# travel in the structured verdict, not only the prose.
BLOCKED_ON = (
    "W0.3 footer gap: "
    + ", ".join(BLOCKED_FIELDS) +
    " not yet emitted (expand A3 to the full five when W0.3 adds them and W4.2 pins required fields)"
)


def _value_for(footer, aliases):
    """The first non-empty value among a field's footer aliases, or None if none is present."""
    for key in aliases:
        if key in footer and footer[key] not in (None, ""):
            return footer[key]
    return None


def _well_formed(field, value):
    """Is this present field well-formed? Presence alone is not enough: a freshness that is not a
    date, or a confidence that is not a tier, is malformed and fails just like a missing field."""
    if field == "source":
        return isinstance(value, str) and value.strip() != ""
    if field == "freshness":
        return bool(_DATE_RE.search(str(value)))
    if field == "confidence":
        return str(value).strip().lower() in CONFIDENCE_TIERS
    return False


def footer_check(footer):
    """Inspect a footer dict against the fields the analyst emits today. Returns a report:
      present     fields that are present and well-formed
      missing     required fields with no value in the footer
      malformed   required fields present but not well-formed
      blocked     the fields V-provenance names that W0.3 does not yet emit (not-yet-checkable)
    The blocked fields are reported, never folded into pass/fail; they are not checkable yet, so
    passing or failing on them would be dishonest either way."""
    footer = footer if isinstance(footer, dict) else {}
    present, missing, malformed = [], [], []
    for field, aliases in REQUIRED_NOW:
        value = _value_for(footer, aliases)
        if value is None:
            missing.append(field)
        elif _well_formed(field, value):
            present.append(field)
        else:
            malformed.append(field)
    return {
        "present": present,
        "missing": missing,
        "malformed": malformed,
        "blocked": dict(BLOCKED_FIELDS),
    }


@register
class ProvenanceGrader(Grader):
    name = "A3-provenance"
    family = "inspection"
    truth_basis = "presence"
    surface = "footer"
    cost_tier = "operational"   # the receipt read; cheap, but it inspects the footer not just the number

    def grade(self, output, *, intensity="decision-grade", run_type="single-number", **ctx):
        """`output` carries the footer as output["footer"] (a dict). Returns a presence SCORE over
        the fields the analyst emits today: pass when all are present and well-formed, fail when
        any is missing or malformed. The blocked fields ride in blocked_on and detail as
        not-yet-checkable, never as a pass."""
        footer = output.get("footer") if isinstance(output, dict) else None
        if not isinstance(footer, dict) or not footer:
            return self.result(
                kind="score", status="fail", value=0.0, blocked_on=BLOCKED_ON,
                detail=("no footer present; the answer carries no receipt. "
                        f"Not-yet-checkable (W0.3): {', '.join(BLOCKED_FIELDS)}. "
                        "A footer makes an answer auditable, not correct."))

        report = footer_check(footer)
        ok = not report["missing"] and not report["malformed"]
        blocked_note = "; ".join(f"{k}: {v}" for k, v in report["blocked"].items())
        detail = (
            f"present {report['present']}, missing {report['missing']}, "
            f"malformed {report['malformed']}. "
            f"Not-yet-checkable (W0.3 footer gap): {blocked_note}. "
            "A footer makes an answer auditable, not correct."
        )
        return self.result(
            kind="score",
            status="pass" if ok else "fail",
            value=1.0 if ok else 0.0,
            detail=detail,
            blocked_on=BLOCKED_ON,
        )
