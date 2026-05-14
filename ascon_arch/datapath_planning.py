from dataclasses import dataclass
from math import ceil

from ascon_arch.config import DatapathConfig
from ascon_arch.enums import DatapathProfile, DatapathWidth, PermutationProfile, TargetTechnology


@dataclass(frozen=True, slots=True)
class DatapathCycleEstimate:
    """Qualitative and simple cycle estimates for one datapath width profile."""

    absorb128_cycles: int
    absorb64_cycles: int
    key128_cycles: int
    tag128_cycles: int
    state320_cycles: int
    area_class: str
    performance_class: str
    io_fit: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "absorb128_cycles": self.absorb128_cycles,
            "absorb64_cycles": self.absorb64_cycles,
            "key128_cycles": self.key128_cycles,
            "tag128_cycles": self.tag128_cycles,
            "state320_cycles": self.state320_cycles,
            "area_class": self.area_class,
            "performance_class": self.performance_class,
            "io_fit": self.io_fit,
            "notes": list(self.notes),
        }


def datapath_config_for_profile(profile: DatapathProfile, target: TargetTechnology) -> DatapathConfig:
    """Build a canonical datapath config for a named width profile."""
    if profile == DatapathProfile.W128:
        return DatapathConfig(
            profile=profile,
            lane_width=DatapathWidth.W128,
            absorb_width=DatapathWidth.W128,
            io_word_width=DatapathWidth.W128,
            serialized_state_update=False,
            serialized_absorb=False,
        )
    if profile == DatapathProfile.W64:
        return DatapathConfig(
            profile=profile,
            lane_width=DatapathWidth.W64,
            absorb_width=DatapathWidth.W64,
            io_word_width=DatapathWidth.W64,
            serialized_state_update=False,
            serialized_absorb=True,
        )
    if profile == DatapathProfile.W32:
        return DatapathConfig(
            profile=profile,
            lane_width=DatapathWidth.W32,
            absorb_width=DatapathWidth.W32,
            io_word_width=DatapathWidth.W32,
            serialized_state_update=True,
            serialized_absorb=True,
        )
    if profile == DatapathProfile.W16:
        return DatapathConfig(
            profile=profile,
            lane_width=DatapathWidth.W16,
            absorb_width=DatapathWidth.W16,
            io_word_width=DatapathWidth.W16,
            serialized_state_update=True,
            serialized_absorb=True,
        )
    if profile == DatapathProfile.W8_SERIAL:
        return DatapathConfig(
            profile=profile,
            lane_width=DatapathWidth.W8,
            absorb_width=DatapathWidth.W8,
            io_word_width=DatapathWidth.W8,
            serialized_state_update=True,
            serialized_absorb=True,
            share_key_registers=True,
            share_pad_logic=True,
        )
    if profile == DatapathProfile.W1_BIT_SERIAL:
        return DatapathConfig(
            profile=profile,
            lane_width=DatapathWidth.W1,
            absorb_width=DatapathWidth.W1,
            io_word_width=DatapathWidth.W8,
            serialized_state_update=True,
            serialized_absorb=True,
            share_key_registers=True,
            share_pad_logic=True,
        )
    if profile == DatapathProfile.W5_SBOX_SERIAL:
        return DatapathConfig(
            profile=profile,
            lane_width=DatapathWidth.W5,
            absorb_width=DatapathWidth.W8,
            io_word_width=DatapathWidth.W8,
            serialized_state_update=True,
            serialized_absorb=True,
            share_key_registers=True,
            share_pad_logic=True,
        )
    raise ValueError(f"unsupported datapath profile: {profile}")


def recommended_datapath_profile(target: TargetTechnology) -> DatapathProfile:
    """Return the current project default for a target family."""
    if target == TargetTechnology.FPGA:
        return DatapathProfile.W128
    return DatapathProfile.W8_SERIAL


def recommended_permutation_profile_for_datapath(
    datapath_profile: DatapathProfile,
    target: TargetTechnology,
) -> PermutationProfile:
    if target == TargetTechnology.FPGA:
        return PermutationProfile.FULLY_PIPELINED
    if datapath_profile == DatapathProfile.W5_SBOX_SERIAL:
        return PermutationProfile.COLUMN_SERIAL
    if datapath_profile == DatapathProfile.W1_BIT_SERIAL:
        return PermutationProfile.BIT_SERIAL
    if datapath_profile in (DatapathProfile.W8_SERIAL, DatapathProfile.W16):
        return PermutationProfile.COLUMN_SERIAL
    return PermutationProfile.ONE_ROUND_PER_CYCLE


def estimate_datapath(config: DatapathConfig) -> DatapathCycleEstimate:
    lane = config.lane_width.bits()
    absorb = config.absorb_width.bits()

    absorb128_cycles = ceil(128 / absorb)
    absorb64_cycles = ceil(64 / absorb)
    key128_cycles = ceil(128 / lane)
    tag128_cycles = ceil(128 / lane)
    state320_cycles = ceil(320 / lane)
    notes: list[str] = []

    if config.profile == DatapathProfile.W128:
        area = "medium_high"
        perf = "best_single_engine"
        io_fit = "excellent_when_external_bus_is_128b_or_wider"
    elif config.profile == DatapathProfile.W64:
        area = "medium"
        perf = "good"
        io_fit = "good_when_external_bus_is_64b"
    elif config.profile == DatapathProfile.W32:
        area = "small_medium"
        perf = "moderate"
        io_fit = "good_for_32b_system_buses"
    elif config.profile == DatapathProfile.W16:
        area = "small"
        perf = "moderate_low"
        io_fit = "reasonable_asic_io_compromise"
        notes.append("candidate ASIC point if 8-bit serial is too slow and 32-bit is too wide")
    elif config.profile == DatapathProfile.W8_SERIAL:
        area = "very_small"
        perf = "low"
        io_fit = "strong_fit_when_asic_io_is_the_bottleneck"
        notes.append("good first tiny-ASIC baseline because byte I/O, padding, and length handling stay natural")
    elif config.profile == DatapathProfile.W1_BIT_SERIAL:
        area = "tiny"
        perf = "very_low"
        io_fit = "poor_unless_io_is_also_bit_serial_or_heavily_buffered"
        notes.append("use mainly for extreme area exploration")
    elif config.profile == DatapathProfile.W5_SBOX_SERIAL:
        area = "tiny"
        perf = "very_low"
        io_fit = "byte_io_with_5bit_internal_sbox_serialization"
        notes.append("separates byte-oriented input handling from a 5-bit physical S-box datapath")
    else:
        area = "unknown"
        perf = "unknown"
        io_fit = "unknown"

    if config.io_word_width.bits() < config.absorb_width.bits():
        notes.append("I/O word is narrower than absorb slice; block assembly buffering is required")
    if config.absorb_width.bits() < 64:
        notes.append("64-bit Hash/XOF rate blocks are serialized across multiple cycles")
    if config.absorb_width.bits() < 128:
        notes.append("AEAD128 128-bit rate blocks are serialized across multiple cycles")

    return DatapathCycleEstimate(
        absorb128_cycles=absorb128_cycles,
        absorb64_cycles=absorb64_cycles,
        key128_cycles=key128_cycles,
        tag128_cycles=tag128_cycles,
        state320_cycles=state320_cycles,
        area_class=area,
        performance_class=perf,
        io_fit=io_fit,
        notes=tuple(notes),
    )
