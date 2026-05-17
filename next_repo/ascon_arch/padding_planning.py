from dataclasses import dataclass

from ascon_arch.config import PaddingConfig
from ascon_arch.enums import LengthHandling, PaddingProfile, PaddingStrategy, TargetTechnology


@dataclass(frozen=True, slots=True)
class PaddingEstimate:
    profile: PaddingProfile
    area_class: str
    flexibility_class: str
    streaming_efficiency: str
    requires_final_bytemask: bool
    requires_total_length: bool
    recommended_target: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.value,
            "area_class": self.area_class,
            "flexibility_class": self.flexibility_class,
            "streaming_efficiency": self.streaming_efficiency,
            "requires_final_bytemask": self.requires_final_bytemask,
            "requires_total_length": self.requires_total_length,
            "recommended_target": self.recommended_target,
            "notes": list(self.notes),
        }


def final_bytemask_width_for_bus(data_bus_bits: int) -> int:
    if data_bus_bits < 8 or data_bus_bits % 8 != 0:
        raise ValueError("data_bus_bits must be a positive byte-aligned width")
    return data_bus_bits // 8


def padding_config_for_profile(
    profile: PaddingProfile,
    target: TargetTechnology,
    *,
    data_bus_bits: int = 128,
) -> PaddingConfig:
    bytemask_width = final_bytemask_width_for_bus(data_bus_bits)

    if profile == PaddingProfile.RTL_PERFORMED:
        return PaddingConfig(
            profile=profile,
            strategy=PaddingStrategy.FSM_ASSISTED,
            length_handling=LengthHandling.INTERNAL_BYTE_COUNTER,
            supports_partial_blocks=True,
            supports_bit_granular_lengths=False,
            supports_arbitrary_byte_lengths=True,
            final_bytemask=False,
            final_bytemask_width=0,
            pad_in_core=True,
            tracks_byte_count=True,
            requires_total_length=False,
            partial_block_buffer_bytes=16,
        )

    if profile == PaddingProfile.FULL_ARBITRARY_BYTELENGTH:
        return PaddingConfig(
            profile=profile,
            strategy=PaddingStrategy.FSM_ASSISTED,
            length_handling=LengthHandling.DESCRIPTOR_BASED,
            supports_partial_blocks=True,
            supports_bit_granular_lengths=False,
            supports_arbitrary_byte_lengths=True,
            final_bytemask=False,
            final_bytemask_width=0,
            pad_in_core=True,
            tracks_byte_count=True,
            requires_total_length=True,
            partial_block_buffer_bytes=max(16, bytemask_width),
        )

    if profile == PaddingProfile.STREAMING_FINAL_BYTEMASK:
        return PaddingConfig(
            profile=profile,
            strategy=PaddingStrategy.INLINE_COMBINATIONAL,
            length_handling=LengthHandling.STREAMING_FINAL_BYTEMASK,
            supports_partial_blocks=True,
            supports_bit_granular_lengths=False,
            supports_arbitrary_byte_lengths=True,
            final_bytemask=True,
            final_bytemask_width=bytemask_width,
            pad_in_core=True,
            tracks_byte_count=False,
            requires_total_length=False,
            partial_block_buffer_bytes=max(16, bytemask_width),
        )

    raise ValueError(f"unsupported padding profile: {profile}")


def recommended_padding_profile(target: TargetTechnology) -> PaddingProfile:
    if target == TargetTechnology.FPGA:
        return PaddingProfile.STREAMING_FINAL_BYTEMASK
    return PaddingProfile.RTL_PERFORMED


def estimate_padding(config: PaddingConfig) -> PaddingEstimate:
    notes: list[str] = []

    if config.profile == PaddingProfile.RTL_PERFORMED:
        area = "medium"
        flex = "medium"
        efficiency = "good"
        recommended = "asic_baseline"
        notes.append("core computes Ascon pad10* internally from byte count and final block state")
        notes.append("recommended first ASIC choice because no upstream bytemask protocol is required")
    elif config.profile == PaddingProfile.FULL_ARBITRARY_BYTELENGTH:
        area = "medium_high"
        flex = "high"
        efficiency = "good"
        recommended = "eventual_full_feature_core"
        notes.append("descriptor or length field supplies exact byte count")
        notes.append("larger because counters, descriptors, and final block assembly are explicit")
    elif config.profile == PaddingProfile.STREAMING_FINAL_BYTEMASK:
        area = "medium"
        flex = "high"
        efficiency = "excellent_streaming"
        recommended = "fpga_streaming_default"
        notes.append("each final stream beat carries a byte-valid mask; the core pads only the invalid tail")
        notes.append("best fit for AXI-stream style valid/ready datapaths and packetized FPGA traffic")
    else:
        area = "unknown"
        flex = "unknown"
        efficiency = "unknown"
        recommended = "unknown"

    if config.supports_bit_granular_lengths:
        notes.append("bit-granular support is enabled; this is beyond the current byte-oriented RTL baseline")
    if config.final_bytemask and config.final_bytemask_width <= 0:
        notes.append("invalid-looking bytemask width; validation should reject this")
    if config.partial_block_buffer_bytes < 16:
        notes.append("partial block buffer is smaller than AEAD128 rate and will need multi-step finalization")

    return PaddingEstimate(
        profile=config.profile,
        area_class=area,
        flexibility_class=flex,
        streaming_efficiency=efficiency,
        requires_final_bytemask=config.final_bytemask,
        requires_total_length=config.requires_total_length,
        recommended_target=recommended,
        notes=tuple(notes),
    )
