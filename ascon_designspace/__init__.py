"""ascon_designspace - the slim, honest replacement for the old architecture
matrix.

Three responsibilities:

* ``axes``     - the vocabulary of the design space (algorithm, datapath,
                 permutation, control, security, topology, ...).
* ``realize``  - the tier model: every point is generated (tier 1), hand-written
                 (tier 2), or specified-but-not-built (tier 3).
* ``catalog``  - enumerate the valid points and attach a realization to each,
                 so the project can say exactly what is specified vs. built.

This package replaces ``ascon_arch``'s skeleton generator. Where the old layer
emitted structural stubs (``assign state_o = state_i; // TODO``), the plan here
is a real generator grown from ``ascon_hwmodel``'s Verilog emission, with the
catalog as its honest front-end. See ``docs/ARCHITECTURE.md``.
"""
from ascon_designspace.catalog import catalog_entries, summarize
from ascon_designspace.realize import (
    DesignPoint,
    Realization,
    RealizationStatus,
    RealizationTier,
    classify,
)

__all__ = [
    "catalog_entries",
    "summarize",
    "classify",
    "DesignPoint",
    "Realization",
    "RealizationStatus",
    "RealizationTier",
]
