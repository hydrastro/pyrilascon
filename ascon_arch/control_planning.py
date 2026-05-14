from dataclasses import dataclass

from ascon_arch.config import ControlConfig, ImplementationConfig
from ascon_arch.enums import (
    AlgorithmFeature,
    ControlProfile,
    InterfaceStyle,
    TargetTechnology,
    TopLevelProfile,
)


@dataclass(frozen=True, slots=True)
class ControlEstimate:
    profile: ControlProfile
    area_class: str
    flexibility_class: str
    scheduler_class: str
    recommended_target: str
    notes: str

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.value,
            "area_class": self.area_class,
            "flexibility_class": self.flexibility_class,
            "scheduler_class": self.scheduler_class,
            "recommended_target": self.recommended_target,
            "notes": self.notes,
        }


def control_config_for_profile(profile: ControlProfile, target: TargetTechnology) -> ControlConfig:
    if profile == ControlProfile.HARDCODED_FSM:
        return ControlConfig(
            profile=profile,
            supports_runtime_algorithm_select=False,
            supports_concurrent_modes=False,
            scheduler_required=False,
        )
    if profile == ControlProfile.MICROCODED_SEQUENCER:
        return ControlConfig(
            profile=profile,
            microcode_words=128,
            supports_runtime_algorithm_select=True,
            supports_concurrent_modes=False,
            supports_descriptors=True,
            scheduler_required=False,
        )
    if profile == ControlProfile.COMMAND_FIFO:
        return ControlConfig(
            profile=profile,
            command_fifo_depth=16 if target == TargetTechnology.FPGA else 4,
            supports_runtime_algorithm_select=True,
            supports_concurrent_modes=True,
            supports_descriptors=True,
            scheduler_required=True,
        )
    if profile == ControlProfile.AXI_STREAM:
        return ControlConfig(
            profile=profile,
            command_fifo_depth=16,
            axi_stream_command_channels=2,
            supports_runtime_algorithm_select=True,
            supports_concurrent_modes=True,
            supports_descriptors=True,
            scheduler_required=True,
        )
    if profile == ControlProfile.AXI_STREAM_MICROCODED_HYBRID:
        return ControlConfig(
            profile=profile,
            microcode_words=256,
            command_fifo_depth=32,
            axi_stream_command_channels=3,
            supports_runtime_algorithm_select=True,
            supports_concurrent_modes=True,
            supports_descriptors=True,
            scheduler_required=True,
        )
    if profile == ControlProfile.CSR_REGISTER_FILE:
        return ControlConfig(
            profile=profile,
            csr_register_count=32,
            supports_runtime_algorithm_select=True,
            supports_concurrent_modes=False,
            supports_descriptors=False,
            scheduler_required=False,
        )
    if profile == ControlProfile.DMA_FED:
        return ControlConfig(
            profile=profile,
            microcode_words=128,
            command_fifo_depth=64,
            csr_register_count=32,
            axi_stream_command_channels=3,
            supports_runtime_algorithm_select=True,
            supports_concurrent_modes=True,
            supports_descriptors=True,
            supports_dma=True,
            scheduler_required=True,
        )
    raise ValueError(f"unsupported control profile: {profile}")


def recommended_control_profile(config: ImplementationConfig) -> ControlProfile:
    if config.target == TargetTechnology.ASIC:
        return ControlProfile.HARDCODED_FSM
    if config.topology.top_level_profile in (
        TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS,
        TopLevelProfile.M_PIPELINES_N_CONTEXTS,
    ):
        return ControlProfile.AXI_STREAM_MICROCODED_HYBRID
    if len(config.algorithm.features) > 1 or any(
        feature in config.algorithm.features
        for feature in (AlgorithmFeature.HASH256, AlgorithmFeature.XOF128, AlgorithmFeature.CXOF128)
    ):
        return ControlProfile.MICROCODED_SEQUENCER
    if config.io.interface_style in (InterfaceStyle.STREAM, InterfaceStyle.DESCRIPTOR_STREAM):
        return ControlProfile.AXI_STREAM
    return ControlProfile.COMMAND_FIFO


def estimate_control(config: ControlConfig) -> ControlEstimate:
    if config.profile == ControlProfile.HARDCODED_FSM:
        return ControlEstimate(config.profile, "very_low", "low", "fixed_phase_fsm", "asic", "Smallest control; best when algorithm/mode set is fixed.")
    if config.profile == ControlProfile.MICROCODED_SEQUENCER:
        return ControlEstimate(config.profile, "medium", "high", "microcode_program_counter", "fpga_or_multi_algo_asic", "Good for AEAD plus Hash/XOF/CXOF or variant support.")
    if config.profile == ControlProfile.COMMAND_FIFO:
        return ControlEstimate(config.profile, "medium", "medium", "fifo_ordered_commands", "fpga_wrapper", "Decouples command issue from datapath execution.")
    if config.profile == ControlProfile.AXI_STREAM:
        return ControlEstimate(config.profile, "medium_high", "high", "stream_command_scheduler", "fpga", "Clean FPGA integration; pairs well with backpressure and descriptor streams.")
    if config.profile == ControlProfile.AXI_STREAM_MICROCODED_HYBRID:
        return ControlEstimate(config.profile, "high", "very_high", "stream_scheduler_plus_microcode", "fpga", "Best fit for multi-context/pipelined FPGA engines supporting several modes.")
    if config.profile == ControlProfile.CSR_REGISTER_FILE:
        return ControlEstimate(config.profile, "medium", "medium", "software_polled_or_interrupt", "fpga_or_soc_asic", "Simple software control; lower throughput unless paired with FIFOs.")
    if config.profile == ControlProfile.DMA_FED:
        return ControlEstimate(config.profile, "very_high", "very_high", "descriptor_dma_scheduler", "fpga", "High-throughput system wrapper, not a tiny core interface.")
    raise ValueError(f"unsupported control profile: {config.profile}")
