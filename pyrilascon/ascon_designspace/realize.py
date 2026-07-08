"""Realization tiers for the ASCON design space.

The design space enumerates hundreds of architecture points. They are not (and
should not be) realized the same way. Every point is classified into one of
three tiers, and the catalog records the classification so the project can
state honestly *what is specified* versus *what is actually built*.

    Tier 1 - GENERATOR    Emitted by the parameterized RTL generator that is
                          grown from the golden model's Verilog emission
                          (``ascon_hwmodel`` already emits a correct 320-bit
                          round; the generator is that emission parameterized by
                          datapath width and rounds-per-cycle). This is the
                          regular, tractable part of the space, and it is the
                          axis TinyTapeout cares about, since narrow serial
                          datapaths are what fit an ASIC tile.

    Tier 2 - HANDWRITTEN  A vetted, hand-written RTL core already implements this
                          point (the working FPGA AEAD128 cores in ``rtl/``).

    Tier 3 - SPECIFIED    Specified in the design space but deliberately not
                          slated for automatic generation. Security
                          countermeasures (masking / threshold / DOM) live here:
                          a generator that emits *unverified* crypto
                          countermeasures is worse than none. Algorithm variants
                          without golden-model KAT support also live here until
                          that support exists.

``RealizationStatus`` is the finer state; ``RealizationTier`` is the coarse
bucket. ``GENERATOR_PLANNED`` means "the generator is intended to cover this
point but is not built for it yet" - as each datapath width lands, points flip
from ``GENERATOR_PLANNED`` to ``GENERATED``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ascon_designspace.generator import GENERATED_PERMUTATION_PROFILES
from ascon_designspace.axes import (
    KAT_BACKED_ALGORITHMS,
    AlgorithmFeature,
    ControlProfile,
    DatapathProfile,
    PaddingProfile,
    PermutationProfile,
    SecurityProfile,
    TargetTechnology,
    TopLevelProfile,
)



class RealizationTier(str, Enum):
    GENERATOR = "tier1_generator"
    HANDWRITTEN = "tier2_handwritten"
    SPECIFIED = "tier3_specified"


class RealizationStatus(str, Enum):
    GENERATED = "generated"                  # tier 1, generator emits it today
    GENERATOR_PLANNED = "generator_planned"  # tier 1, intended, not built yet
    HANDWRITTEN = "handwritten"              # tier 2
    SPECIFIED_ONLY = "specified_only"        # tier 3

    @property
    def tier(self) -> RealizationTier:
        if self in (RealizationStatus.GENERATED, RealizationStatus.GENERATOR_PLANNED):
            return RealizationTier.GENERATOR
        if self is RealizationStatus.HANDWRITTEN:
            return RealizationTier.HANDWRITTEN
        return RealizationTier.SPECIFIED


@dataclass(frozen=True, slots=True)
class DesignPoint:
    """One coordinate in the ASCON architecture design space."""

    target: TargetTechnology
    algorithm: AlgorithmFeature
    top_level: TopLevelProfile
    datapath: DatapathProfile
    permutation: PermutationProfile
    control: ControlProfile
    padding: PaddingProfile
    security: SecurityProfile

    def label(self) -> str:
        return (
            f"{self.target.value}/{self.algorithm.value}/{self.top_level.value}/"
            f"dp={self.datapath.value}/perm={self.permutation.value}/"
            f"ctrl={self.control.value}/sec={self.security.value}"
        )


@dataclass(frozen=True, slots=True)
class Realization:
    status: RealizationStatus
    note: str = ""
    source: str = ""  # generator module or hand-written core path, when known

    @property
    def tier(self) -> RealizationTier:
        return self.status.tier


# --- Tier 2 registry: points a vetted hand-written core already implements. ---
# Encoded as a predicate so it stays readable; extend as more cores are vetted.
# Today: the working FPGA AEAD128 128-bit AXI-stream cores at 4 and 8 rounds
# per cycle.
_HANDWRITTEN_FPGA_PERMS = frozenset(
    {
        PermutationProfile.FOUR_ROUNDS_PER_CYCLE,
        PermutationProfile.EIGHT_ROUNDS_PER_CYCLE,
    }
)


def _handwritten_core(p: DesignPoint) -> Realization | None:
    if (
        p.target is TargetTechnology.FPGA
        and p.algorithm is AlgorithmFeature.AEAD128
        and p.datapath is DatapathProfile.W128
        and p.permutation in _HANDWRITTEN_FPGA_PERMS
        and p.security is SecurityProfile.NONE
    ):
        rpc = "4rpc" if p.permutation is PermutationProfile.FOUR_ROUNDS_PER_CYCLE else "8rpc"
        return Realization(
            status=RealizationStatus.HANDWRITTEN,
            note=f"vetted FPGA AEAD128 {rpc} core",
            source=f"rtl/common/ascon_accel_axis128_aead128_{rpc}_top.v",
        )
    return None


# Datapath widths the parameterized generator targets (regular + tractable).
# Narrow/serial widths are the TinyTapeout-relevant ones.
_GENERATOR_DATAPATHS = frozenset(
    {
        DatapathProfile.W128,
        DatapathProfile.W64,
        DatapathProfile.W32,
        DatapathProfile.W16,
        DatapathProfile.W8_SERIAL,
        DatapathProfile.W5_SBOX_SERIAL,
        DatapathProfile.W1_BIT_SERIAL,
    }
)


# Permutation profiles the generator emits + verifies today (round-based family).
# The rest (fully-pipelined, column-serial, bit-serial) are the next increment.
GENERATOR_COVERED_PERMS = frozenset(
    PermutationProfile(profile) for profile in GENERATED_PERMUTATION_PROFILES
)


def classify(p: DesignPoint) -> Realization:
    """Assign a realization to a design point (honest first-cut policy).

    Order matters: security and KAT-backing gate everything, because those are
    correctness/verification constraints, not performance ones. Only after those
    gates do we ask whether a hand-written core exists or the generator covers
    the point.
    """
    # Tier 3 gate: security countermeasures are never auto-generated.
    if p.security is not SecurityProfile.NONE:
        return Realization(
            status=RealizationStatus.SPECIFIED_ONLY,
            note=(
                f"security profile '{p.security.value}' is Tier 3 "
                f"(hand-write + verify when built; never auto-generated)"
            ),
        )
    # Tier 3 gate: algorithms the golden model cannot verify yet.
    if p.algorithm not in KAT_BACKED_ALGORITHMS:
        return Realization(
            status=RealizationStatus.SPECIFIED_ONLY,
            note=f"algorithm '{p.algorithm.value}' has no golden-model KAT support yet",
        )
    # Tier 2: a vetted hand-written core exists.
    hw = _handwritten_core(p)
    if hw is not None:
        return hw
    # Tier 1: on the generator's target axes.
    if p.datapath in _GENERATOR_DATAPATHS:
        if p.permutation in GENERATOR_COVERED_PERMS:
            return Realization(
                status=RealizationStatus.GENERATED,
                note="round-based permutation core generated + model-verified; I/O wrapper is stage 3b",
                source="ascon_designspace.generator.permutation",
            )
        return Realization(
            status=RealizationStatus.GENERATOR_PLANNED,
            note="on the generator axes; bit-serial permutation is the remaining increment",
            source="ascon_designspace.generator (grown from ascon_hwmodel emission)",
        )
    return Realization(
        status=RealizationStatus.SPECIFIED_ONLY,
        note="not slated for generation",
    )
