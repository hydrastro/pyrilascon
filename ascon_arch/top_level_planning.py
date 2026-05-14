from dataclasses import dataclass

from ascon_arch.config import ImplementationConfig
from ascon_arch.enums import TopLevelProfile


@dataclass(frozen=True, slots=True)
class TopLevelEstimate:
    """Qualitative estimate for the top-level core/pipeline organization."""

    profile: TopLevelProfile
    aead_core_count: int
    permutation_pipeline_count: int
    context_count: int
    contexts_per_pipeline: int
    expected_parallel_operations: int
    throughput_class: str
    area_class: str
    scheduling_class: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.value,
            "aead_core_count": self.aead_core_count,
            "permutation_pipeline_count": self.permutation_pipeline_count,
            "context_count": self.context_count,
            "contexts_per_pipeline": self.contexts_per_pipeline,
            "expected_parallel_operations": self.expected_parallel_operations,
            "throughput_class": self.throughput_class,
            "area_class": self.area_class,
            "scheduling_class": self.scheduling_class,
            "notes": list(self.notes),
        }


def estimate_top_level(config: ImplementationConfig) -> TopLevelEstimate:
    topology = config.topology
    context = config.context
    profile = topology.top_level_profile
    notes: list[str] = []

    if profile == TopLevelProfile.SINGLE_CORE:
        throughput = "one_aead_operation_at_a_time"
        area = "small"
        scheduling = "single_core_fsm"
        notes.append("one logical AEAD operation progresses at a time")
    elif profile == TopLevelProfile.DUAL_ENC_DEC_CORES:
        throughput = "independent_encrypt_and_decrypt"
        area = "medium_high"
        scheduling = "two_core_or_two_datapath_dispatch"
        notes.append("one encrypt and one decrypt operation can progress independently")
    elif profile == TopLevelProfile.N_IDENTICAL_AEAD_CORES:
        throughput = "near_linear_packet_parallel_scaling"
        area = "scales_with_core_count"
        scheduling = "packet_dispatch_across_identical_cores"
        notes.append("simple FPGA scaling for independent packets/messages")
    elif profile == TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS:
        throughput = "aggregate_context_interleaved_pipeline"
        area = "medium_high"
        scheduling = "single_pipeline_context_interleaving"
        notes.append("one permutation pipeline is shared by many contexts")
    elif profile == TopLevelProfile.M_PIPELINES_N_CONTEXTS:
        throughput = "extreme_context_interleaved_pipeline_parallelism"
        area = "very_high"
        scheduling = "multi_pipeline_context_scheduler"
        notes.append("multiple permutation pipelines consume contexts in parallel")
    else:
        throughput = "unknown"
        area = "unknown"
        scheduling = "unknown"

    if topology.contexts_per_pipeline > 1:
        notes.append(f"{topology.contexts_per_pipeline} contexts are assigned per permutation pipeline")
    if topology.permutation_pipeline_count > 1:
        notes.append(f"{topology.permutation_pipeline_count} permutation pipelines are instantiated")
    if context.context_count > 1:
        notes.append(f"total visible contexts: {context.context_count}")

    return TopLevelEstimate(
        profile=profile,
        aead_core_count=topology.aead_core_count,
        permutation_pipeline_count=topology.permutation_pipeline_count,
        context_count=context.context_count,
        contexts_per_pipeline=topology.contexts_per_pipeline,
        expected_parallel_operations=topology.expected_parallel_operations(),
        throughput_class=throughput,
        area_class=area,
        scheduling_class=scheduling,
        notes=tuple(notes),
    )
