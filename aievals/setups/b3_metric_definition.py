"""B3 Metric definition (canonical layer L3): the proven setup, and the reference for the rest.

Staging a meaning-only metric contract is the one Track B unit already proven end to end (the
retention contract collapses the drift). This module registers it as the reference SetupSpec and
gives the builder the other context units copy: it returns a Setup that points a source-reader
at the contract, with no hardcoded analyst path (the caller supplies the directory the contract
lives in, or omits it to use our canonical teaching fixture).
"""
from aievals.harness.setups import Setup
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup


def build(contract_dir=None, **ctx):
    """Return the with-definition setup. `contract_dir` is the directory holding the contract
    YAML (analyst-side when testing a real analyst); defaults to our canonical fixture dir so the
    setup is runnable hermetically. The baseline (no definition) is simply Setup(name=..., layer=
    None, spec=None)."""
    spec = str(contract_dir) if contract_dir is not None else str(FIXTURES)
    return Setup(name="with-retention-definition", layer="L3", reader="file", spec=spec)


def baseline():
    """The no-definition arm: the bare baseline the with-definition arm is compared against."""
    return Setup(name="no-definition", layer=None, reader="file", spec=None)


register_setup(SetupSpec(
    key="B3-metric-definition",
    layer="L3",
    status="buildable-now",
    summary="Stage a meaning-only metric contract on or off; the proven drift-collapsing setup.",
    source="C-store.md, FRAMEWORK_v0 §2; proven live (retention)",
    build=build,
))
