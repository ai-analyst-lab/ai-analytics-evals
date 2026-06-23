"""B-skills Skills as context (cross-cutting axis, layer=None): the turn-zero footprint measurement.

The reliability thesis from the skills/tools/instructions research is that an agent's behavior is
governed by what is RESIDENT in the context window at turn 0 (before any work starts), not by how
large the skill or tool library is on disk. A 65-skill system whose descriptions cost a few thousand
resident tokens is healthier than a 10-tool system with every schema inlined. So the thing worth
measuring is not the catalog size but the resident footprint: the sum of the metadata (skill
descriptions, non-deferred tool schemas) that enters the prefix every turn.

This unit provides that measurement. `skills_footprint` takes the resident skill/tool descriptors
(each a name plus its turn-0 token cost) and returns the total resident footprint plus the per-skill
breakdown, so a builder can see which entries dominate the budget. It is deliberately a pure sum over
the inputs handed to it: nothing here invents a token count, and there is no result number baked into
the module. The descriptors carry the measured tokens (from `count_tokens` on the real prefix); this
unit only totals and itemizes them.

There is no setup to toggle here, so the registered SetupSpec carries build=None: this is a
cross-cutting measurement axis, not a context layer the comparison run stages on and off. It is
buildable now because the measurement function works and is tested; the honest caveat from the source
is that the descriptor tokens must come from a real `count_tokens` reading, not an eyeballed estimate.

Source: book/research/C-skills-context.md (section 3, the resident-footprint metric).
"""
from aievals.setups.base import SetupSpec, register_setup


def skills_footprint(skills):
    """Measure the resident token footprint of a set of skill/tool descriptors at turn 0.

    `skills` is a list of descriptors, each a mapping with at least:
      name    the skill or tool identifier (used as the breakdown label)
      tokens  its resident cost at turn 0 (the description/schema tokens, from count_tokens)

    Returns a dict:
      total_tokens   the sum of every descriptor's resident tokens (the budget tax paid every turn)
      breakdown      a list of {name, tokens} in input order, so a builder sees which entries dominate
      skill_count    how many descriptors were measured (the resident set size, not the catalog size)

    The footprint is exactly the sum of what is handed in: this is the resident layer (metadata only),
    not the skill bodies that stay on disk until a task matches them. No token count is invented here.
    """
    if skills is None:
        raise TypeError("skills must be a list of descriptors, not None")
    breakdown = []
    total = 0
    for i, s in enumerate(skills):
        if "name" not in s or "tokens" not in s:
            raise ValueError(f"descriptor {i} needs both 'name' and 'tokens'; got {sorted(s)}")
        tokens = int(s["tokens"])
        if tokens < 0:
            raise ValueError(f"descriptor {s['name']!r} has negative tokens {tokens}")
        breakdown.append({"name": s["name"], "tokens": tokens})
        total += tokens
    return {"total_tokens": total, "breakdown": breakdown, "skill_count": len(breakdown)}


register_setup(SetupSpec(
    key="B-skills",
    layer=None,
    status="buildable-now",
    summary="Turn-zero footprint measurement: sum the resident skill/tool metadata tokens (not the "
            "catalog size); skills_footprint(skills) totals and itemizes the per-skill cost.",
    source="C-skills-context.md",
    build=None,
))
