from dataclasses import dataclass
from math import ceil

from ascon_arch.config import ContextConfig
from ascon_arch.enums import (
    ContextProfile,
    ContextSchedulingStyle,
    StateStorageStyle,
    TargetTechnology,
)


@dataclass(frozen=True, slots=True)
class ContextStorageEstimate:
    profile: ContextProfile
    storage: StateStorageStyle
    context_count: int
    contexts_per_engine: int
    interleave_depth: int
    state_bits_total: int
    state_register_equivalent_bits: int
    memory_bits: int
    area_class: str
    scheduling_class: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.value,
            "storage": self.storage.value,
            "context_count": self.context_count,
            "contexts_per_engine": self.contexts_per_engine,
            "interleave_depth": self.interleave_depth,
            "state_bits_total": self.state_bits_total,
            "state_register_equivalent_bits": self.state_register_equivalent_bits,
            "memory_bits": self.memory_bits,
            "area_class": self.area_class,
            "scheduling_class": self.scheduling_class,
            "notes": list(self.notes),
        }


def _id_bits(count: int) -> int:
    if count <= 1:
        return 0
    return (count - 1).bit_length()


def context_config_for_profile(
    profile: ContextProfile,
    target: TargetTechnology,
    *,
    engine_count: int = 1,
    contexts_per_engine: int | None = None,
    pipeline_stages: int = 0,
) -> ContextConfig:
    """Build a canonical context/state-storage configuration.

    The profiles are architectural intent, not RTL implementation. They keep the
    scheduling and storage choices explicit so later backends can bind them to
    registers, LUTRAM, BRAM, SRAM, or a context scheduler.
    """
    if engine_count < 1:
        raise ValueError("engine_count must be >= 1")

    if profile == ContextProfile.SINGLE_320_REGISTER:
        # One 320-bit state per active datapath. A separate enc/dec ASIC can
        # still have two active states because it has two datapaths; each state
        # remains a plain 320-bit register with no context scheduler.
        cpe = 1 if contexts_per_engine is None else contexts_per_engine
        total = max(1, engine_count * cpe)
        return ContextConfig(
            profile=profile,
            scheduling=ContextSchedulingStyle.SINGLE_CONTEXT,
            storage=StateStorageStyle.SINGLE_CONTEXT_REGS,
            context_count=total,
            contexts_per_engine=cpe,
            interleave_depth=1,
            context_id_bits=_id_bits(total),
            shadow_state=False,
            rollback_supported=False,
            state_memory_read_ports=1,
            state_memory_write_ports=1,
        )

    if profile == ContextProfile.STATE_PLUS_SHADOW:
        cpe = 1 if contexts_per_engine is None else contexts_per_engine
        total = max(1, engine_count * cpe)
        return ContextConfig(
            profile=profile,
            scheduling=ContextSchedulingStyle.SINGLE_CONTEXT,
            storage=StateStorageStyle.STATE_PLUS_SHADOW_REGS,
            context_count=total,
            contexts_per_engine=cpe,
            interleave_depth=1,
            context_id_bits=_id_bits(total),
            shadow_state=True,
            rollback_supported=True,
            state_memory_read_ports=1,
            state_memory_write_ports=1,
        )

    if profile == ContextProfile.MULTI_CONTEXT_REGISTERS:
        cpe = contexts_per_engine or max(2, pipeline_stages or 2)
        total = engine_count * cpe
        return ContextConfig(
            profile=profile,
            scheduling=ContextSchedulingStyle.STATIC_INTERLEAVED,
            storage=StateStorageStyle.MULTI_CONTEXT_REGFILE,
            context_count=total,
            contexts_per_engine=cpe,
            interleave_depth=cpe,
            context_id_bits=_id_bits(total),
            shadow_state=False,
            rollback_supported=False,
            state_memory_read_ports=1,
            state_memory_write_ports=1,
        )

    if profile == ContextProfile.FPGA_BRAM_LUTRAM:
        if target != TargetTechnology.FPGA:
            raise ValueError("fpga_bram_lutram context profile is FPGA-specific")
        cpe = contexts_per_engine or max(2, pipeline_stages or 2)
        total = engine_count * cpe
        # Small context banks usually infer LUTRAM; larger banks may become BRAM.
        storage = StateStorageStyle.FPGA_LUTRAM_CONTEXT_MEMORY if total <= 64 else StateStorageStyle.FPGA_BRAM_CONTEXT_MEMORY
        return ContextConfig(
            profile=profile,
            scheduling=ContextSchedulingStyle.DYNAMIC_QUEUE,
            storage=storage,
            context_count=total,
            contexts_per_engine=cpe,
            interleave_depth=cpe,
            context_id_bits=_id_bits(total),
            shadow_state=False,
            rollback_supported=False,
            state_memory_read_ports=1,
            state_memory_write_ports=1,
        )

    if profile == ContextProfile.SEPARATE_STATE_PER_CORE:
        total = engine_count
        return ContextConfig(
            profile=profile,
            scheduling=ContextSchedulingStyle.SINGLE_CONTEXT,
            storage=StateStorageStyle.SEPARATE_STATE_PER_CORE,
            context_count=total,
            contexts_per_engine=1,
            interleave_depth=1,
            context_id_bits=_id_bits(total),
            shadow_state=False,
            rollback_supported=False,
            state_memory_read_ports=1,
            state_memory_write_ports=1,
        )

    if profile == ContextProfile.SHARED_STATE_RAM_PIPELINED_P8:
        cpe = contexts_per_engine or max(8, pipeline_stages or 8)
        total = engine_count * cpe
        return ContextConfig(
            profile=profile,
            scheduling=ContextSchedulingStyle.STATIC_INTERLEAVED,
            storage=StateStorageStyle.SHARED_STATE_RAM_PIPELINED_P8,
            context_count=total,
            contexts_per_engine=cpe,
            interleave_depth=cpe,
            context_id_bits=_id_bits(total),
            shadow_state=False,
            rollback_supported=False,
            state_memory_read_ports=1,
            state_memory_write_ports=1,
        )

    raise ValueError(f"unsupported context profile: {profile}")


def recommended_context_profile(target: TargetTechnology, *, fully_pipelined: bool = False) -> ContextProfile:
    if target == TargetTechnology.FPGA:
        if fully_pipelined:
            return ContextProfile.FPGA_BRAM_LUTRAM
        return ContextProfile.MULTI_CONTEXT_REGISTERS
    return ContextProfile.SINGLE_320_REGISTER


def estimate_context_storage(config: ContextConfig) -> ContextStorageEstimate:
    multiplier = 2 if config.shadow_state else 1
    state_bits_total = 320 * config.context_count * multiplier
    memory_backed = config.storage in (
        StateStorageStyle.FPGA_BRAM_CONTEXT_MEMORY,
        StateStorageStyle.FPGA_LUTRAM_CONTEXT_MEMORY,
        StateStorageStyle.ASIC_SRAM_CONTEXT_MEMORY,
        StateStorageStyle.SHARED_STATE_RAM_PIPELINED_P8,
    )
    memory_bits = state_bits_total if memory_backed else 0
    reg_bits = 0 if memory_backed else state_bits_total
    notes: list[str] = []

    if config.profile == ContextProfile.SINGLE_320_REGISTER:
        area = "smallest"
        scheduling = "single_context_no_interleave"
        notes.append("plain 320-bit state register per active datapath")
    elif config.profile == ContextProfile.STATE_PLUS_SHADOW:
        area = "small_debug_friendly"
        scheduling = "single_context_with_rollback"
        notes.append("adds a shadow copy for debug, rollback, or speculative phase handling")
    elif config.profile == ContextProfile.MULTI_CONTEXT_REGISTERS:
        area = "medium"
        scheduling = "interleaved_register_contexts"
        notes.append("lets one permutation engine switch among independent contexts")
    elif config.profile == ContextProfile.FPGA_BRAM_LUTRAM:
        area = "medium_fpga_memory_backed"
        scheduling = "dynamic_or_static_multisession"
        notes.append("maps naturally to FPGA LUTRAM/BRAM session storage")
    elif config.profile == ContextProfile.SEPARATE_STATE_PER_CORE:
        area = "scales_with_core_count"
        scheduling = "simple_multicore"
        notes.append("simplest N-core scaling: one state bank per engine/core")
    elif config.profile == ContextProfile.SHARED_STATE_RAM_PIPELINED_P8:
        area = "area_efficient_multisession"
        scheduling = "interleaved_shared_pipeline"
        notes.append("targets a shared state RAM feeding a pipelined round/p8 engine")
    else:
        area = "unknown"
        scheduling = "unknown"

    if config.interleave_depth > 1:
        notes.append(f"requires at least {config.interleave_depth} active contexts per engine for full interleave utilization")
    if config.context_id_bits > 0:
        notes.append(f"context id width: {config.context_id_bits} bits")

    return ContextStorageEstimate(
        profile=config.profile,
        storage=config.storage,
        context_count=config.context_count,
        contexts_per_engine=config.contexts_per_engine,
        interleave_depth=config.interleave_depth,
        state_bits_total=state_bits_total,
        state_register_equivalent_bits=reg_bits,
        memory_bits=memory_bits,
        area_class=area,
        scheduling_class=scheduling,
        notes=tuple(notes),
    )
