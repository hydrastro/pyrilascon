"""Validity rules for the ASCON design space.

This replaces the old ``ascon_arch.validation`` (~750 lines that operated on a
fully-resolved ``ImplementationConfig``). Empirically, only four rule *types*
reject any point in the current design-space grids, so those are encoded here as
real predicates on the resolved fields - not a truth table overfit to the grid,
but the actual semantics, so the rules stay correct if the axes expand.

``validate`` returns ``None`` for a valid point, or a human-readable reason for
an invalid one. The catalog is regression-locked to the exact counts these rules
produce (ASIC 352, FPGA 208, 560 total); if a future axis needs a rule that is
in ``validation.py`` but never fired for the current grids, add it here and the
counts move deliberately.
"""
from __future__ import annotations

from ascon_designspace.axes import (
    DatapathProfile,
    PermutationStyle,
    TopLevelProfile,
)
from ascon_designspace.resolve import ResolvedPoint, resolve

# Topologies that interleave multiple contexts through a permutation pipeline.
_CONTEXT_INTERLEAVED = (
    TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS,
    TopLevelProfile.M_PIPELINES_N_CONTEXTS,
)


def validate(point) -> str | None:
    """Return None if the design point is valid, else a reason string."""
    r: ResolvedPoint = resolve(point)

    # --- Permutation-vs-datapath geometry -----------------------------------
    if r.permutation_style is PermutationStyle.BIT_SERIAL:
        if r.lane_width_bits > 16:
            return "bit_serial should use a very narrow datapath lane (<=16 bits)"

    if r.permutation_style is PermutationStyle.COLUMN_SERIAL:
        if point.datapath is DatapathProfile.W128:
            return "column_serial should not be paired with a 128-bit datapath profile"
        if r.lane_width_bits > 64:
            return "column_serial should use a narrow datapath lane (<=64 bits)"
        if r.sbox_columns_per_cycle >= 64:
            return "column_serial should use fewer than 64 S-box columns per cycle"

    # --- Context-interleaved pipeline topologies ----------------------------
    if point.top_level in _CONTEXT_INTERLEAVED:
        if not r.control_has_scheduler:
            return "context-interleaved pipeline topologies require a scheduler-capable control profile"
        if not r.is_pipelined_permutation:
            if point.top_level is TopLevelProfile.M_PIPELINES_N_CONTEXTS:
                return "multi-pipeline context topologies require a pipelined permutation config"
            return "context-interleaved pipeline topologies require a pipelined permutation config"

    return None


def is_valid(point) -> bool:
    return validate(point) is None
