"""The new validity rules must reproduce the exact accept/reject behavior of the
four rules that fired in the old validation, on both targets."""
from ascon_designspace.axes import (
    ControlProfile,
    DatapathProfile,
    PaddingProfile,
    PermutationProfile,
    SecurityProfile,
    TargetTechnology,
    TopLevelProfile,
    AlgorithmFeature,
)
from ascon_designspace.realize import DesignPoint
from ascon_designspace.rules import is_valid, validate


def _asic(dp, perm, sec=SecurityProfile.NONE):
    return DesignPoint(
        target=TargetTechnology.ASIC,
        algorithm=AlgorithmFeature.AEAD128,
        top_level=TopLevelProfile.DUAL_ENC_DEC_CORES,
        datapath=dp,
        permutation=perm,
        control=ControlProfile.HARDCODED_FSM,
        padding=PaddingProfile.RTL_PERFORMED,
        security=sec,
    )


def _fpga(top, perm, ctrl, sec=SecurityProfile.NONE):
    return DesignPoint(
        target=TargetTechnology.FPGA,
        algorithm=AlgorithmFeature.AEAD128,
        top_level=top,
        datapath=DatapathProfile.W128,
        permutation=perm,
        control=ctrl,
        padding=PaddingProfile.STREAMING_FINAL_BYTEMASK,
        security=sec,
    )


def test_bit_serial_needs_narrow_lane() -> None:
    # >16-bit lanes are rejected; <=16-bit lanes are accepted.
    assert not is_valid(_asic(DatapathProfile.W64, PermutationProfile.BIT_SERIAL))
    assert not is_valid(_asic(DatapathProfile.W32, PermutationProfile.BIT_SERIAL))
    assert is_valid(_asic(DatapathProfile.W16, PermutationProfile.BIT_SERIAL))
    assert is_valid(_asic(DatapathProfile.W1_BIT_SERIAL, PermutationProfile.BIT_SERIAL))


def test_non_bit_serial_asic_points_are_valid() -> None:
    for dp in (DatapathProfile.W64, DatapathProfile.W32, DatapathProfile.W16):
        assert is_valid(_asic(dp, PermutationProfile.ONE_ROUND_PER_CYCLE))
        assert is_valid(_asic(dp, PermutationProfile.COLUMN_SERIAL))


def test_context_interleaved_needs_scheduler_control() -> None:
    # MICROCODED_SEQUENCER has no scheduler -> rejected on interleaved tops.
    p = _fpga(
        TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS,
        PermutationProfile.FULLY_PIPELINED,
        ControlProfile.MICROCODED_SEQUENCER,
    )
    assert validate(p) == (
        "context-interleaved pipeline topologies require a scheduler-capable control profile"
    )


def test_context_interleaved_needs_pipelined_permutation() -> None:
    # Scheduler-capable control but a non-pipelined perm -> rejected.
    p = _fpga(
        TopLevelProfile.M_PIPELINES_N_CONTEXTS,
        PermutationProfile.FOUR_ROUNDS_PER_CYCLE,
        ControlProfile.AXI_STREAM,
    )
    assert validate(p) == "multi-pipeline context topologies require a pipelined permutation config"


def test_context_interleaved_happy_path() -> None:
    for top in (
        TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS,
        TopLevelProfile.M_PIPELINES_N_CONTEXTS,
    ):
        for ctrl in (ControlProfile.AXI_STREAM, ControlProfile.AXI_STREAM_MICROCODED_HYBRID):
            assert is_valid(_fpga(top, PermutationProfile.FULLY_PIPELINED, ctrl))


def test_n_identical_cores_have_no_topology_restriction() -> None:
    # Every perm/control combo on the parallel-cores top is valid.
    for perm in (
        PermutationProfile.FOUR_ROUNDS_PER_CYCLE,
        PermutationProfile.EIGHT_ROUNDS_PER_CYCLE,
        PermutationProfile.FULLY_PIPELINED,
    ):
        for ctrl in (
            ControlProfile.AXI_STREAM,
            ControlProfile.MICROCODED_SEQUENCER,
            ControlProfile.AXI_STREAM_MICROCODED_HYBRID,
        ):
            assert is_valid(_fpga(TopLevelProfile.N_IDENTICAL_AEAD_CORES, perm, ctrl))
