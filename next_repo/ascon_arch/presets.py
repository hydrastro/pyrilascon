from dataclasses import replace

from ascon_arch.config import (
    AlgorithmConfig,
    ContextConfig,
    ControlConfig,
    DatapathConfig,
    DatapathTopology,
    IOConfig,
    ImplementationConfig,
    PaddingConfig,
    PermutationConfig,
    RtlConfig,
    SecurityConfig,
)
from ascon_arch.enums import (
    AlgorithmFeature,
    ArchitectureFamily,
    ContextProfile,
    ContextSchedulingStyle,
    ControlProfile,
    DatapathProfile,
    DatapathWidth,
    EngineCapability,
    FlowControlStyle,
    InterfaceStyle,
    LengthHandling,
    PaddingProfile,
    PaddingStrategy,
    PermutationProfile,
    PermutationStyle,
    ResetStyle,
    RtlLanguage,
    SBoxStyle,
    SecurityProfile,
    SideChannelProtection,
    StateStorageStyle,
    TargetTechnology,
    TopLevelProfile,
)
from ascon_arch.permutation_planning import permutation_config_for_profile
from ascon_arch.datapath_planning import datapath_config_for_profile
from ascon_arch.context_planning import context_config_for_profile
from ascon_arch.control_planning import control_config_for_profile
from ascon_arch.padding_planning import padding_config_for_profile
from ascon_arch.security_planning import security_config_for_profile
from ascon_arch.algorithm_planning import algorithm_config_for_feature, algorithm_name_suffix


def shared_datapath_config(target: TargetTechnology, name: str = "shared_datapath") -> ImplementationConfig:
    return ImplementationConfig(
        name=name,
        target=target,
        algorithm=AlgorithmConfig(features=(AlgorithmFeature.AEAD128,), include_encrypt=True, include_decrypt=True),
        topology=DatapathTopology(
            family=ArchitectureFamily.SHARED_DATAPATH,
            engine_count=1,
            engine_capability=EngineCapability.AEAD_ENCRYPT_DECRYPT,
            shared_encrypt_decrypt_datapath=True,
            encrypt_datapaths_per_engine=1,
            decrypt_datapaths_per_engine=1,
            shared_permutation_per_engine=True,
            mode_fsm_count_per_engine=1,
            top_level_profile=TopLevelProfile.SINGLE_CORE,
            aead_core_count=1,
        ),
        permutation=PermutationConfig(
            style=PermutationStyle.ROUND_SERIAL,
            sbox_style=SBoxStyle.BOOLEAN,
            rounds_per_cycle=1,
            pipeline_stages=0,
            unroll_factor=1,
            share_round_logic=True,
        ),
        datapath=replace(
            datapath_config_for_profile(DatapathProfile.W64, target),
            split_encrypt_decrypt_control=False,
            share_key_registers=True,
            share_pad_logic=True,
        ),
        context=context_config_for_profile(
            ContextProfile.SINGLE_320_REGISTER,
            target,
            engine_count=1,
        ),
        padding=padding_config_for_profile(
            PaddingProfile.RTL_PERFORMED,
            target,
            data_bus_bits=128,
        ),
        io=IOConfig(
            interface_style=InterfaceStyle.STREAM,
            data_bus_bits=128,
            supports_backpressure=True,
            flow_control=FlowControlStyle.VALID_READY,
        ),
        control=control_config_for_profile(
            ControlProfile.HARDCODED_FSM if target == TargetTechnology.ASIC else ControlProfile.AXI_STREAM,
            target,
        ),
        security=security_config_for_profile(
            SecurityProfile.ASIC_BASELINE if target == TargetTechnology.ASIC else SecurityProfile.FPGA_FAULT_DETECT,
            target,
        ),
        rtl=RtlConfig(language=RtlLanguage.SYSTEMVERILOG, reset_style=ResetStyle.ASYNC_ACTIVE_LOW),
        description="Single shared AEAD datapath. Lowest/medium area; one operation progresses at a time.",
    )


def asic_two_datapaths_config() -> ImplementationConfig:
    """ASIC baseline chosen by the user: separate encryption and decryption datapaths."""
    return ImplementationConfig(
        name="asic_two_datapaths",
        target=TargetTechnology.ASIC,
        algorithm=AlgorithmConfig(features=(AlgorithmFeature.AEAD128,), include_encrypt=True, include_decrypt=True),
        topology=DatapathTopology(
            family=ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS,
            engine_count=1,
            engine_capability=EngineCapability.AEAD_ENCRYPT_DECRYPT,
            shared_encrypt_decrypt_datapath=False,
            encrypt_datapaths_per_engine=1,
            decrypt_datapaths_per_engine=1,
            shared_permutation_per_engine=False,
            mode_fsm_count_per_engine=2,
            top_level_profile=TopLevelProfile.DUAL_ENC_DEC_CORES,
            aead_core_count=2,
        ),
        permutation=PermutationConfig(
            style=PermutationStyle.ROUND_SERIAL,
            sbox_style=SBoxStyle.BOOLEAN,
            rounds_per_cycle=1,
            pipeline_stages=0,
            unroll_factor=1,
            register_between_rounds=False,
            share_round_logic=True,
        ),
        datapath=replace(
            datapath_config_for_profile(DatapathProfile.W64, TargetTechnology.ASIC),
            split_encrypt_decrypt_control=True,
            share_key_registers=False,
            share_pad_logic=True,
        ),
        context=context_config_for_profile(
            ContextProfile.SINGLE_320_REGISTER,
            TargetTechnology.ASIC,
            engine_count=2,
            contexts_per_engine=1,
        ),
        padding=padding_config_for_profile(
            PaddingProfile.RTL_PERFORMED,
            TargetTechnology.ASIC,
            data_bus_bits=128,
        ),
        io=IOConfig(
            interface_style=InterfaceStyle.STREAM,
            data_bus_bits=128,
            supports_backpressure=True,
            flow_control=FlowControlStyle.VALID_READY,
            separate_encrypt_decrypt_ports=True,
        ),
        control=control_config_for_profile(ControlProfile.HARDCODED_FSM, TargetTechnology.ASIC),
        security=security_config_for_profile(SecurityProfile.ASIC_BASELINE, TargetTechnology.ASIC),
        rtl=RtlConfig(language=RtlLanguage.SYSTEMVERILOG, reset_style=ResetStyle.ASYNC_ACTIVE_LOW),
        description=(
            "ASIC architecture with independent AEAD encryption and decryption datapaths. "
            "This costs more area than a shared datapath but allows one encrypt and one decrypt operation to progress concurrently."
        ),
    )


def shared_permutation_mode_fsm_config(target: TargetTechnology = TargetTechnology.ASIC) -> ImplementationConfig:
    """Medium-area compromise: separate mode FSM/control around a single permutation bottleneck."""
    return ImplementationConfig(
        name=f"{target.value}_shared_permutation_mode_fsm",
        target=target,
        algorithm=AlgorithmConfig(features=(AlgorithmFeature.AEAD128,), include_encrypt=True, include_decrypt=True),
        topology=DatapathTopology(
            family=ArchitectureFamily.SHARED_PERMUTATION_MODE_FSM,
            engine_count=1,
            engine_capability=EngineCapability.AEAD_ENCRYPT_DECRYPT,
            shared_encrypt_decrypt_datapath=False,
            encrypt_datapaths_per_engine=1,
            decrypt_datapaths_per_engine=1,
            shared_permutation_per_engine=True,
            mode_fsm_count_per_engine=1,
            top_level_profile=TopLevelProfile.SINGLE_CORE,
            aead_core_count=1,
        ),
        permutation=PermutationConfig(
            style=PermutationStyle.ROUND_SERIAL,
            sbox_style=SBoxStyle.BOOLEAN if target == TargetTechnology.ASIC else SBoxStyle.LUT5,
            rounds_per_cycle=1,
            pipeline_stages=0,
            share_round_logic=True,
        ),
        datapath=replace(
            datapath_config_for_profile(DatapathProfile.W64, target),
            split_encrypt_decrypt_control=False,
            share_key_registers=True,
            share_pad_logic=True,
        ),
        context=context_config_for_profile(
            ContextProfile.SINGLE_320_REGISTER,
            target,
            engine_count=1,
        ),
        padding=padding_config_for_profile(
            PaddingProfile.RTL_PERFORMED,
            target,
            data_bus_bits=128,
        ),
        io=IOConfig(interface_style=InterfaceStyle.STREAM, data_bus_bits=128, supports_backpressure=True),
        control=control_config_for_profile(
            ControlProfile.HARDCODED_FSM if target == TargetTechnology.ASIC else ControlProfile.MICROCODED_SEQUENCER,
            target,
        ),
        security=security_config_for_profile(
            SecurityProfile.ASIC_BASELINE if target == TargetTechnology.ASIC else SecurityProfile.FPGA_FAULT_DETECT,
            target,
        ),
        rtl=RtlConfig(language=RtlLanguage.SYSTEMVERILOG, reset_style=ResetStyle.ASYNC_ACTIVE_LOW),
        description="Separate mode control around a single shared permutation engine. Medium area, one permutation bottleneck.",
    )


def fpga_n_parallel_engines_config(engine_count: int) -> ImplementationConfig:
    """FPGA baseline chosen by the user: N independent parallel engines."""
    return ImplementationConfig(
        name=f"fpga_{engine_count}_parallel_engines",
        target=TargetTechnology.FPGA,
        algorithm=AlgorithmConfig(
            features=(AlgorithmFeature.AEAD128, AlgorithmFeature.HASH256, AlgorithmFeature.XOF128, AlgorithmFeature.CXOF128),
            include_encrypt=True,
            include_decrypt=True,
            include_hash=True,
            include_xof=True,
            include_cxof=True,
        ),
        topology=DatapathTopology(
            family=ArchitectureFamily.PARALLEL_ENGINES,
            engine_count=engine_count,
            engine_capability=EngineCapability.AEAD_HASH_XOF,
            shared_encrypt_decrypt_datapath=False,
            encrypt_datapaths_per_engine=1,
            decrypt_datapaths_per_engine=1,
            shared_permutation_per_engine=False,
            mode_fsm_count_per_engine=1,
            top_level_profile=TopLevelProfile.N_IDENTICAL_AEAD_CORES,
            aead_core_count=engine_count,
        ),
        permutation=permutation_config_for_profile(
            PermutationProfile.FULLY_PIPELINED,
            TargetTechnology.FPGA,
            sbox_style=SBoxStyle.LUT5,
        ),
        datapath=replace(
            datapath_config_for_profile(DatapathProfile.W128, TargetTechnology.FPGA),
            split_encrypt_decrypt_control=True,
            share_key_registers=False,
            share_pad_logic=False,
        ),
        context=context_config_for_profile(
            ContextProfile.FPGA_BRAM_LUTRAM,
            TargetTechnology.FPGA,
            engine_count=engine_count,
            contexts_per_engine=12,
            pipeline_stages=12,
        ),
        padding=padding_config_for_profile(
            PaddingProfile.STREAMING_FINAL_BYTEMASK,
            TargetTechnology.FPGA,
            data_bus_bits=128 * engine_count,
        ),
        io=IOConfig(
            interface_style=InterfaceStyle.DESCRIPTOR_STREAM,
            data_bus_bits=128 * engine_count,
            supports_backpressure=True,
            flow_control=FlowControlStyle.VALID_READY,
        ),
        control=control_config_for_profile(ControlProfile.AXI_STREAM_MICROCODED_HYBRID, TargetTechnology.FPGA),
        security=security_config_for_profile(SecurityProfile.FPGA_FAULT_DETECT, TargetTechnology.FPGA),
        rtl=RtlConfig(language=RtlLanguage.SYSTEMVERILOG, reset_style=ResetStyle.ASYNC_ACTIVE_LOW),
        description=(
            "FPGA architecture with N independent ASCON engines. Area scales roughly with N; "
            "throughput should scale close to linearly for independent messages if memory/I/O can feed all engines."
        ),
    )



def config_with_algorithm_feature(
    config: ImplementationConfig,
    feature: AlgorithmFeature,
    *,
    name_suffix: str | None = None,
) -> ImplementationConfig:
    """Return a copy of a design config specialized for one algorithm feature.

    This keeps the design-space sweep orthogonal: topology/datapath/control choices
    can be counted across AEAD, HASH, XOF, and CXOF architecture targets, while
    production verification status remains tracked separately by the golden model and KATs.
    """
    suffix = name_suffix or algorithm_name_suffix(feature)
    return replace(
        config,
        name=f"{config.name}_{suffix}",
        algorithm=algorithm_config_for_feature(feature),
    )


def config_with_permutation_profile(
    config: ImplementationConfig,
    profile: PermutationProfile,
    *,
    name_suffix: str | None = None,
    sbox_style: SBoxStyle | None = None,
) -> ImplementationConfig:
    """Return a copy of a design config using one named permutation profile."""
    permutation = permutation_config_for_profile(profile, config.target, sbox_style=sbox_style)
    suffix = name_suffix or profile.value
    return replace(config, name=f"{config.name}_{suffix}", permutation=permutation)


def asic_two_datapaths_two_rounds_per_cycle_config() -> ImplementationConfig:
    return config_with_permutation_profile(
        asic_two_datapaths_config(),
        PermutationProfile.TWO_ROUNDS_PER_CYCLE,
        name_suffix="2rpc",
        sbox_style=SBoxStyle.BOOLEAN,
    )


def asic_two_datapaths_column_serial_config() -> ImplementationConfig:
    base = asic_two_datapaths_config()
    narrow_datapath = replace(
        datapath_config_for_profile(DatapathProfile.W5_SBOX_SERIAL, TargetTechnology.ASIC),
        split_encrypt_decrypt_control=True,
        share_key_registers=True,
        share_pad_logic=True,
    )
    return replace(
        config_with_permutation_profile(
            base,
            PermutationProfile.COLUMN_SERIAL,
            name_suffix="column_serial",
            sbox_style=SBoxStyle.BOOLEAN,
        ),
        datapath=narrow_datapath,
    )


def config_with_datapath_profile(
    config: ImplementationConfig,
    profile: DatapathProfile,
    *,
    name_suffix: str | None = None,
) -> ImplementationConfig:
    """Return a copy of a design config using one named datapath width profile."""
    base = datapath_config_for_profile(profile, config.target)
    datapath = replace(
        base,
        rate_width_bits=config.datapath.rate_width_bits,
        key_width_bits=config.datapath.key_width_bits,
        tag_width_bits=config.datapath.tag_width_bits,
        split_encrypt_decrypt_control=config.datapath.split_encrypt_decrypt_control,
        share_key_registers=config.datapath.share_key_registers if profile not in (DatapathProfile.W8_SERIAL, DatapathProfile.W1_BIT_SERIAL, DatapathProfile.W5_SBOX_SERIAL) else True,
        share_pad_logic=config.datapath.share_pad_logic if profile not in (DatapathProfile.W8_SERIAL, DatapathProfile.W1_BIT_SERIAL, DatapathProfile.W5_SBOX_SERIAL) else True,
    )
    suffix = name_suffix or profile.value
    data_bus_bits = datapath.io_word_width.bits() * config.topology.engine_count
    io = replace(config.io, data_bus_bits=data_bus_bits)
    padding = config.padding
    if padding.final_bytemask:
        padding = replace(padding, final_bytemask_width=max(1, data_bus_bits // 8))
    return replace(config, name=f"{config.name}_{suffix}", datapath=datapath, io=io, padding=padding)


def asic_two_datapaths_with_datapath_profile_config(profile: DatapathProfile) -> ImplementationConfig:
    base = asic_two_datapaths_config()
    config = config_with_datapath_profile(base, profile)
    if profile == DatapathProfile.W5_SBOX_SERIAL:
        return config_with_permutation_profile(config, PermutationProfile.COLUMN_SERIAL, sbox_style=SBoxStyle.BOOLEAN)
    if profile == DatapathProfile.W1_BIT_SERIAL:
        return config_with_permutation_profile(config, PermutationProfile.BIT_SERIAL, sbox_style=SBoxStyle.BOOLEAN)
    if profile in (DatapathProfile.W8_SERIAL, DatapathProfile.W16):
        return config_with_permutation_profile(config, PermutationProfile.COLUMN_SERIAL, sbox_style=SBoxStyle.BOOLEAN)
    return config


def fpga_n_parallel_engines_with_datapath_profile_config(engine_count: int, profile: DatapathProfile) -> ImplementationConfig:
    base = fpga_n_parallel_engines_config(engine_count)
    return config_with_datapath_profile(base, profile)


def fpga_n_parallel_engines_with_profile_config(engine_count: int, profile: PermutationProfile) -> ImplementationConfig:
    sbox = SBoxStyle.LUT5 if profile in (
        PermutationProfile.FOUR_ROUNDS_PER_CYCLE,
        PermutationProfile.EIGHT_ROUNDS_PER_CYCLE,
        PermutationProfile.FULLY_PIPELINED,
    ) else SBoxStyle.BOOLEAN
    base = fpga_n_parallel_engines_config(engine_count)
    return config_with_permutation_profile(base, profile, sbox_style=sbox)


def config_with_context_profile(
    config: ImplementationConfig,
    profile: ContextProfile,
    *,
    contexts_per_engine: int | None = None,
    name_suffix: str | None = None,
) -> ImplementationConfig:
    """Return a copy of a design config using one named state/context organization profile."""
    if profile == ContextProfile.SINGLE_320_REGISTER and config.topology.family == ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS:
        engine_count_for_context = config.topology.total_encrypt_datapaths() + config.topology.total_decrypt_datapaths()
    else:
        engine_count_for_context = config.topology.engine_count
    context = context_config_for_profile(
        profile,
        config.target,
        engine_count=engine_count_for_context,
        contexts_per_engine=contexts_per_engine,
        pipeline_stages=config.permutation.pipeline_stages,
    )
    suffix = name_suffix or profile.value
    return replace(config, name=f"{config.name}_{suffix}", context=context)


def asic_two_datapaths_with_context_profile_config(profile: ContextProfile) -> ImplementationConfig:
    return config_with_context_profile(asic_two_datapaths_config(), profile)


def fpga_n_parallel_engines_with_context_profile_config(
    engine_count: int,
    profile: ContextProfile,
    *,
    contexts_per_engine: int | None = None,
) -> ImplementationConfig:
    return config_with_context_profile(
        fpga_n_parallel_engines_config(engine_count),
        profile,
        contexts_per_engine=contexts_per_engine,
    )



def config_with_control_profile(
    config: ImplementationConfig,
    profile: ControlProfile,
    *,
    name_suffix: str | None = None,
) -> ImplementationConfig:
    """Return a copy using one named control/sequencing organization profile."""
    control = control_config_for_profile(profile, config.target)
    suffix = name_suffix or profile.value
    padding = config.padding
    if profile == ControlProfile.DMA_FED:
        padding = padding_config_for_profile(
            PaddingProfile.FULL_ARBITRARY_BYTELENGTH,
            config.target,
            data_bus_bits=config.io.data_bus_bits,
        )
    return replace(config, name=f"{config.name}_{suffix}", control=control, padding=padding)


def asic_two_datapaths_hardcoded_fsm_config() -> ImplementationConfig:
    return config_with_control_profile(asic_two_datapaths_config(), ControlProfile.HARDCODED_FSM, name_suffix="hardcoded_fsm")


def fpga_n_parallel_engines_with_control_profile_config(engine_count: int, profile: ControlProfile) -> ImplementationConfig:
    return config_with_control_profile(fpga_n_parallel_engines_config(engine_count), profile)




def config_with_security_profile(
    config: ImplementationConfig,
    profile: SecurityProfile,
    *,
    name_suffix: str | None = None,
    plaintext_buffer_capacity_bytes: int | None = None,
) -> ImplementationConfig:
    """Return a copy using one named security/fault/decryption-release profile."""
    security = security_config_for_profile(
        profile,
        config.target,
        plaintext_buffer_capacity_bytes=plaintext_buffer_capacity_bytes,
    )
    suffix = name_suffix or profile.value
    return replace(config, name=f"{config.name}_{suffix}", security=security)


def config_with_padding_profile(
    config: ImplementationConfig,
    profile: PaddingProfile,
    *,
    name_suffix: str | None = None,
) -> ImplementationConfig:
    """Return a copy using one named padding/final-length handling profile."""
    padding = padding_config_for_profile(
        profile,
        config.target,
        data_bus_bits=config.io.data_bus_bits,
    )
    suffix = name_suffix or profile.value
    return replace(config, name=f"{config.name}_{suffix}", padding=padding)


def _resize_padding_for_io(config: ImplementationConfig, io: IOConfig) -> PaddingConfig:
    if not config.padding.final_bytemask:
        return config.padding
    return replace(config.padding, final_bytemask_width=max(1, io.data_bus_bits // 8))


def config_with_top_level_profile(
    config: ImplementationConfig,
    profile: TopLevelProfile,
    *,
    core_count: int | None = None,
    pipeline_count: int | None = None,
    contexts_per_pipeline: int | None = None,
    name_suffix: str | None = None,
) -> ImplementationConfig:
    """Return a copy using one top-level core/pipeline organization profile."""
    suffix = name_suffix or profile.value

    if profile == TopLevelProfile.SINGLE_CORE:
        topology = replace(
            config.topology,
            top_level_profile=profile,
            engine_count=1,
            aead_core_count=1,
            permutation_pipeline_count=0,
            contexts_per_pipeline=1,
            shared_pipeline_across_contexts=False,
        )
        context = context_config_for_profile(ContextProfile.SINGLE_320_REGISTER, config.target, engine_count=1)
        io = replace(config.io, data_bus_bits=config.datapath.io_word_width.bits())
        return replace(config, name=f"{config.name}_{suffix}", topology=topology, context=context, io=io, padding=_resize_padding_for_io(config, io))

    if profile == TopLevelProfile.DUAL_ENC_DEC_CORES:
        topology = replace(
            config.topology,
            family=ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS,
            engine_count=1,
            engine_capability=EngineCapability.AEAD_ENCRYPT_DECRYPT,
            shared_encrypt_decrypt_datapath=False,
            encrypt_datapaths_per_engine=1,
            decrypt_datapaths_per_engine=1,
            shared_permutation_per_engine=False,
            mode_fsm_count_per_engine=2,
            top_level_profile=profile,
            aead_core_count=2,
            permutation_pipeline_count=0,
            contexts_per_pipeline=1,
            shared_pipeline_across_contexts=False,
        )
        context = context_config_for_profile(ContextProfile.SINGLE_320_REGISTER, config.target, engine_count=2)
        io = replace(config.io, separate_encrypt_decrypt_ports=True)
        return replace(config, name=f"{config.name}_{suffix}", topology=topology, context=context, io=io, padding=_resize_padding_for_io(config, io))

    if profile == TopLevelProfile.N_IDENTICAL_AEAD_CORES:
        n = core_count or config.topology.engine_count
        topology = replace(
            config.topology,
            family=ArchitectureFamily.PARALLEL_ENGINES,
            engine_count=n,
            engine_capability=EngineCapability.AEAD_HASH_XOF,
            top_level_profile=profile,
            aead_core_count=n,
            permutation_pipeline_count=0,
            contexts_per_pipeline=1,
            shared_pipeline_across_contexts=False,
        )
        context = context_config_for_profile(
            ContextProfile.FPGA_BRAM_LUTRAM if config.target == TargetTechnology.FPGA else ContextProfile.SEPARATE_STATE_PER_CORE,
            config.target,
            engine_count=n,
            contexts_per_engine=config.context.contexts_per_engine,
            pipeline_stages=config.permutation.pipeline_stages,
        )
        io = replace(config.io, data_bus_bits=config.datapath.io_word_width.bits() * n)
        return replace(config, name=f"{config.name}_{suffix}_{n}", topology=topology, context=context, io=io, padding=_resize_padding_for_io(config, io))

    if profile == TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS:
        ctx = contexts_per_pipeline or max(config.context.contexts_per_engine, config.permutation.pipeline_stages, 2)
        topology = replace(
            config.topology,
            family=ArchitectureFamily.SHARED_PERMUTATION_MODE_FSM,
            engine_count=1,
            engine_capability=EngineCapability.AEAD_HASH_XOF,
            shared_encrypt_decrypt_datapath=False,
            shared_permutation_per_engine=True,
            mode_fsm_count_per_engine=1,
            top_level_profile=profile,
            aead_core_count=1,
            permutation_pipeline_count=1,
            contexts_per_pipeline=ctx,
            shared_pipeline_across_contexts=True,
        )
        context = context_config_for_profile(
            ContextProfile.FPGA_BRAM_LUTRAM,
            config.target,
            engine_count=1,
            contexts_per_engine=ctx,
            pipeline_stages=max(config.permutation.pipeline_stages, ctx),
        )
        io = replace(config.io, data_bus_bits=config.datapath.io_word_width.bits())
        return replace(config, name=f"{config.name}_{suffix}_{ctx}ctx", topology=topology, context=context, io=io, padding=_resize_padding_for_io(config, io))

    if profile == TopLevelProfile.M_PIPELINES_N_CONTEXTS:
        m = pipeline_count or max(config.topology.permutation_pipeline_count, 2)
        ctx = contexts_per_pipeline or max(config.context.contexts_per_engine, config.permutation.pipeline_stages, 2)
        topology = replace(
            config.topology,
            family=ArchitectureFamily.SHARED_PERMUTATION_MODE_FSM,
            engine_count=m,
            engine_capability=EngineCapability.AEAD_HASH_XOF,
            shared_encrypt_decrypt_datapath=False,
            shared_permutation_per_engine=True,
            mode_fsm_count_per_engine=1,
            top_level_profile=profile,
            aead_core_count=m,
            permutation_pipeline_count=m,
            contexts_per_pipeline=ctx,
            shared_pipeline_across_contexts=True,
        )
        context = context_config_for_profile(
            ContextProfile.FPGA_BRAM_LUTRAM,
            config.target,
            engine_count=m,
            contexts_per_engine=ctx,
            pipeline_stages=max(config.permutation.pipeline_stages, ctx),
        )
        io = replace(config.io, data_bus_bits=config.datapath.io_word_width.bits() * m)
        return replace(config, name=f"{config.name}_{suffix}_{m}p_{ctx}ctx", topology=topology, context=context, io=io, padding=_resize_padding_for_io(config, io))

    raise ValueError(f"unsupported top-level profile: {profile}")


def fpga_one_pipelined_permutation_n_contexts_config(contexts_per_pipeline: int = 12) -> ImplementationConfig:
    base = fpga_n_parallel_engines_config(2)
    return config_with_top_level_profile(
        base,
        TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS,
        contexts_per_pipeline=contexts_per_pipeline,
        name_suffix="one_pipeline",
    )


def fpga_m_pipelines_n_contexts_config(pipeline_count: int = 2, contexts_per_pipeline: int = 12) -> ImplementationConfig:
    base = fpga_n_parallel_engines_config(max(2, pipeline_count))
    return config_with_top_level_profile(
        base,
        TopLevelProfile.M_PIPELINES_N_CONTEXTS,
        pipeline_count=pipeline_count,
        contexts_per_pipeline=contexts_per_pipeline,
        name_suffix="m_pipelines",
    )


def asic_dual_enc_dec_cores_config() -> ImplementationConfig:
    return config_with_top_level_profile(
        asic_two_datapaths_config(),
        TopLevelProfile.DUAL_ENC_DEC_CORES,
        name_suffix="dual_cores",
    )
