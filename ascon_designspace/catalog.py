"""The ASCON architecture catalog: enumerate the design space and record, for
every valid point, how it is realized (generator / hand-written / specified).

The honest front-end of the generator. It enumerates the valid architecture
points and tags each with a realization tier, so the project can state exactly
what is *specified* versus what is *built*.

Self-contained as of stage 2: enumeration and validity live entirely in this
package (``axes`` + ``resolve`` + ``rules``); the old ``ascon_arch`` is gone. The
counts are unchanged (ASIC 352, FPGA 208, 560 total) and regression-locked by
``tests/test_designspace_catalog.py``.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product

from ascon_designspace.axes import (
    REQUESTED_SINGLE_ALGORITHM_FEATURES,
    ControlProfile,
    DatapathProfile,
    PaddingProfile,
    PermutationProfile,
    SecurityProfile,
    TargetTechnology,
    TopLevelProfile,
)
from ascon_designspace.realize import (
    DesignPoint,
    Realization,
    RealizationStatus,
    RealizationTier,
    classify,
)
from ascon_designspace.rules import validate


@dataclass(frozen=True, slots=True)
class _AxisGrid:
    """The axis values swept for one target. The cartesian product of these,
    filtered by ``rules.validate``, is the valid design space for the target."""

    tops: tuple[TopLevelProfile, ...]
    datapaths: tuple[DatapathProfile, ...]
    perms: tuple[PermutationProfile, ...]
    controls: tuple[ControlProfile, ...]
    paddings: tuple[PaddingProfile, ...]
    securities: tuple[SecurityProfile, ...]


_ASIC_GRID = _AxisGrid(
    tops=(TopLevelProfile.DUAL_ENC_DEC_CORES,),
    datapaths=(
        DatapathProfile.W64,
        DatapathProfile.W32,
        DatapathProfile.W16,
        DatapathProfile.W8_SERIAL,
        DatapathProfile.W5_SBOX_SERIAL,
        DatapathProfile.W1_BIT_SERIAL,
    ),
    perms=(
        PermutationProfile.ONE_ROUND_PER_CYCLE,
        PermutationProfile.TWO_ROUNDS_PER_CYCLE,
        PermutationProfile.COLUMN_SERIAL,
        PermutationProfile.BIT_SERIAL,
    ),
    controls=(ControlProfile.HARDCODED_FSM,),
    paddings=(PaddingProfile.RTL_PERFORMED,),
    securities=(SecurityProfile.NONE, SecurityProfile.ASIC_BASELINE),
)

_FPGA_GRID = _AxisGrid(
    tops=(
        TopLevelProfile.N_IDENTICAL_AEAD_CORES,
        TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS,
        TopLevelProfile.M_PIPELINES_N_CONTEXTS,
    ),
    datapaths=(DatapathProfile.W128,),
    perms=(
        PermutationProfile.FOUR_ROUNDS_PER_CYCLE,
        PermutationProfile.EIGHT_ROUNDS_PER_CYCLE,
        PermutationProfile.FULLY_PIPELINED,
    ),
    controls=(
        ControlProfile.AXI_STREAM,
        ControlProfile.MICROCODED_SEQUENCER,
        ControlProfile.AXI_STREAM_MICROCODED_HYBRID,
    ),
    paddings=(PaddingProfile.STREAMING_FINAL_BYTEMASK,),
    securities=(SecurityProfile.NONE, SecurityProfile.FPGA_FAULT_DETECT),
)

_GRIDS: dict[TargetTechnology, _AxisGrid] = {
    TargetTechnology.ASIC: _ASIC_GRID,
    TargetTechnology.FPGA: _FPGA_GRID,
}


def _valid_points(target: TargetTechnology, algorithms):
    grid = _GRIDS[target]
    for top, algo, dp, perm, ctrl, pad, sec in product(
        grid.tops, algorithms, grid.datapaths, grid.perms, grid.controls, grid.paddings, grid.securities
    ):
        point = DesignPoint(
            target=target,
            algorithm=algo,
            top_level=top,
            datapath=dp,
            permutation=perm,
            control=ctrl,
            padding=pad,
            security=sec,
        )
        if validate(point) is None:
            yield point


def catalog_entries(
    *,
    targets: tuple[TargetTechnology, ...] = (TargetTechnology.ASIC, TargetTechnology.FPGA),
    algorithms=REQUESTED_SINGLE_ALGORITHM_FEATURES,
) -> list[tuple[DesignPoint, Realization]]:
    """Every valid design point paired with its realization."""
    entries: list[tuple[DesignPoint, Realization]] = []
    for target in targets:
        for point in _valid_points(target, algorithms):
            entries.append((point, classify(point)))
    return entries


def summarize(
    *,
    targets: tuple[TargetTechnology, ...] = (TargetTechnology.ASIC, TargetTechnology.FPGA),
    algorithms=REQUESTED_SINGLE_ALGORITHM_FEATURES,
) -> dict:
    """Counts by target, tier, and finer status."""
    entries = catalog_entries(targets=targets, algorithms=algorithms)
    by_target: Counter = Counter()
    by_tier: Counter = Counter()
    by_status: Counter = Counter()
    for point, real in entries:
        by_target[point.target] += 1
        by_tier[real.tier] += 1
        by_status[real.status] += 1
    return {
        "total": len(entries),
        "by_target": dict(by_target),
        "by_tier": dict(by_tier),
        "by_status": dict(by_status),
    }


def _fmt_summary(s: dict) -> str:
    tgt, tier, status = s["by_target"], s["by_tier"], s["by_status"]

    def g(d, k):
        return d.get(k, 0)

    return "\n".join(
        [
            "ASCON design-space catalog",
            f"  total valid points : {s['total']}"
            f"   (ASIC {g(tgt, TargetTechnology.ASIC)}, FPGA {g(tgt, TargetTechnology.FPGA)})",
            "",
            "  by realization tier:",
            f"    tier1 generator   : {g(tier, RealizationTier.GENERATOR):4d}"
            f"   ({g(status, RealizationStatus.GENERATED)} generated,"
            f" {g(status, RealizationStatus.GENERATOR_PLANNED)} planned)",
            f"    tier2 handwritten : {g(tier, RealizationTier.HANDWRITTEN):4d}"
            f"   (vetted RTL cores exist today)",
            f"    tier3 specified   : {g(tier, RealizationTier.SPECIFIED):4d}"
            f"   (security countermeasures + non-KAT algorithms)",
        ]
    )


def main() -> None:
    print(_fmt_summary(summarize()))


if __name__ == "__main__":
    main()
