"""Graders: one uniform shape for every validation check.

See `aievals.graders.base` for the interface, the six grader families, the four intensity
rungs, and the selector. Individual checks (A1-A10) live in their own modules and self-register.
"""
from aievals.graders.base import (  # noqa: F401
    FAMILIES,
    KINDS,
    TRUTH_BASES,
    RUNGS,
    RUN_TYPES,
    GraderResult,
    Grader,
    register,
    registry,
    by_family,
    family_table,
    select_graders,
)
