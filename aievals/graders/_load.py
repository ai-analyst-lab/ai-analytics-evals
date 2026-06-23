"""Autoloader for grader modules.

Graders self-register on import (the @register decorator). This imports every grader module in
this package so the registry is populated without a central hand-edited list, which keeps new
graders from colliding on a shared file. Call load_all() before reading the registry.
"""
import importlib
import pkgutil


def load_all():
    """Import every grader module (the a*.py checks) so each self-registers."""
    import aievals.graders as pkg
    for info in pkgutil.iter_modules(pkg.__path__):
        if info.name.startswith("_") or info.name == "base":
            continue
        importlib.import_module(f"aievals.graders.{info.name}")
