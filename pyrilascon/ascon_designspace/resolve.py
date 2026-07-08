"""Resolve a design point's coordinates into the derived, RTL-relevant fields.

The old ``ascon_arch`` presets expanded each coordinate into a large
``ImplementationConfig`` with many sub-configs. Most of those fields only fed the
skeleton emitter (expected-metrics/manifest metadata) and are gone. What remains
here is the lean set of derived facts that the validity rules need today and that
the parameterized generator will consume in stage 3:

* ``lane_width_bits``          - datapath lane width in bits
* ``sbox_columns_per_cycle``   - S-box columns processed per cycle
* ``permutation_style``        - structural style of the permutation
* ``is_pipelined_permutation`` - whether the permutation is a filled pipeline
                                 (the only profile that is, today, is
                                 FULLY_PIPELINED)
* ``control_has_scheduler``    - whether the control profile can schedule
                                 interleaved pipeline contexts

The mappings mirror the datapath/permutation/control planning that the old
package performed, distilled to the fields that matter.
"""
from __future__ import annotations

from dataclasses import dataclass

from ascon_designspace.axes import (
    ControlProfile,
    DatapathProfile,
    DatapathWidth,
    PermutationProfile,
    PermutationStyle,
)

# datapath profile -> physical lane width
_LANE_WIDTH: dict[DatapathProfile, DatapathWidth] = {
    DatapathProfile.W128: DatapathWidth.W128,
    DatapathProfile.W64: DatapathWidth.W64,
    DatapathProfile.W32: DatapathWidth.W32,
    DatapathProfile.W16: DatapathWidth.W16,
    DatapathProfile.W8_SERIAL: DatapathWidth.W8,
    DatapathProfile.W1_BIT_SERIAL: DatapathWidth.W1,
    DatapathProfile.W5_SBOX_SERIAL: DatapathWidth.W5,
}

# permutation profile -> (style, sbox_columns_per_cycle, is_pipelined)
_PERMUTATION: dict[PermutationProfile, tuple[PermutationStyle, int, bool]] = {
    PermutationProfile.ONE_ROUND_PER_CYCLE: (PermutationStyle.ROUND_SERIAL, 64, False),
    PermutationProfile.TWO_ROUNDS_PER_CYCLE: (PermutationStyle.ROUND_UNROLLED, 64, False),
    PermutationProfile.FOUR_ROUNDS_PER_CYCLE: (PermutationStyle.ROUND_UNROLLED, 64, False),
    PermutationProfile.EIGHT_ROUNDS_PER_CYCLE: (PermutationStyle.ROUND_UNROLLED, 64, False),
    PermutationProfile.FULLY_PIPELINED: (PermutationStyle.ROUND_PIPELINED, 64, True),
    PermutationProfile.COLUMN_SERIAL: (PermutationStyle.COLUMN_SERIAL, 1, False),
    PermutationProfile.BIT_SERIAL: (PermutationStyle.BIT_SERIAL, 1, False),
}

# control profile -> can it schedule interleaved pipeline contexts?
_CONTROL_HAS_SCHEDULER: dict[ControlProfile, bool] = {
    ControlProfile.HARDCODED_FSM: False,
    ControlProfile.MICROCODED_SEQUENCER: False,
    ControlProfile.COMMAND_FIFO: True,
    ControlProfile.AXI_STREAM: True,
    ControlProfile.AXI_STREAM_MICROCODED_HYBRID: True,
    ControlProfile.CSR_REGISTER_FILE: False,
    ControlProfile.DMA_FED: True,
}


@dataclass(frozen=True, slots=True)
class ResolvedPoint:
    lane_width_bits: int
    sbox_columns_per_cycle: int
    permutation_style: PermutationStyle
    is_pipelined_permutation: bool
    control_has_scheduler: bool


def lane_width_bits(datapath: DatapathProfile) -> int:
    return _LANE_WIDTH[datapath].bits()


def control_has_scheduler(control: ControlProfile) -> bool:
    return _CONTROL_HAS_SCHEDULER[control]


def resolve(point) -> ResolvedPoint:
    """Resolve the derived fields of a DesignPoint (see ``realize.DesignPoint``)."""
    style, sbox_cols, pipelined = _PERMUTATION[point.permutation]
    return ResolvedPoint(
        lane_width_bits=lane_width_bits(point.datapath),
        sbox_columns_per_cycle=sbox_cols,
        permutation_style=style,
        is_pipelined_permutation=pipelined,
        control_has_scheduler=control_has_scheduler(point.control),
    )
