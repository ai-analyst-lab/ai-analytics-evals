"""Track B setups: the Context Stack as testable, toggleable setups.

See `aievals.setups.base` for the SetupSpec registry and the honest status vocabulary. Each
context unit (B0-B7, B-format, B-granularity, B-home, ...) lives in its own module and
self-registers. Call load_all() before reading the registry.
"""
import importlib
import pkgutil

from aievals.setups.base import (  # noqa: F401
    SetupSpec,
    STATUSES,
    register_setup,
    registry,
    by_status,
    status_table,
)

# Where the canonical worked content lives (the meaning-only retention contract reused by the
# format, granularity, and home experiments). Our own teaching fixture, not an analyst path.
from pathlib import Path
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_all():
    """Import every setup module so each self-registers its SetupSpec."""
    import aievals.setups as pkg
    for info in pkgutil.iter_modules(pkg.__path__):
        if info.name.startswith("_") or info.name == "base":
            continue
        importlib.import_module(f"aievals.setups.{info.name}")
