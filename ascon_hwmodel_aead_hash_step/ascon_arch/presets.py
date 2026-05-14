from dataclasses import replace

from ascon_arch.config import (
    AlgorithmConfig,
    ContextConfig,
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
    DatapathProfile,
    DatapathWidth,
    EngineCapability,
    FlowControlStyle,
    InterfaceStyle,
    LengthHandling,
    PaddingStrategy,
    PermutationProfile,
    PermutationStyle,
    ResetStyle,
    RtlLanguage,
    SBoxStyle,
    SideChannelProtection,
    StateStorageStyle,
    TargetTechnology,
)
from ascon_arch.permutation_planning import permutation_config_for_profile
from ascon_arch.datapath_planning import datapath_config_for_profile
from ascon_arch.context_planning import context_config_for_profile


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
        padding=PaddingConfig(
            strategy=PaddingStrategy.FSM_ASSISTED,
            length_handling=LengthHandling.INTERNAL_BYTE_COUNTER,
        ),
        io=IOConfig(
            interface_style=InterfaceStyle.STREAM,
            data_bus_bits=128,
            supports_backpressure=True,
            flow_control=FlowControlStyle.VALID_READY,
        ),
        security=SecurityConfig(
            side_channel_protection=SideChannelProtection.NONE,
            constant_time_control=True,
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
        padding=PaddingConfig(
            strategy=PaddingStrategy.FSM_ASSISTED,
            length_handling=LengthHandling.INTERNAL_BYTE_COUNTER,
            supports_partial_blocks=True,
        ),
        io=IOConfig(
            interface_style=InterfaceStyle.STREAM,
            data_bus_bits=128,
            supports_backpressure=True,
            flow_control=FlowControlStyle.VALID_READY,
            separate_encrypt_decrypt_ports=True,
        ),
        security=SecurityConfig(
            side_channel_protection=SideChannelProtection.NONE,
            constant_time_control=True,
            clear_state_on_done=True,
        ),
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
        padding=PaddingConfig(strategy=PaddingStrategy.FSM_ASSISTED, length_handling=LengthHandling.INTERNAL_BYTE_COUNTER),
        io=IOConfig(interface_style=InterfaceStyle.STREAM, data_bus_bits=128, supports_backpressure=True),
        security=SecurityConfig(side_channel_protection=SideChannelProtection.NONE, constant_time_control=True),
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
        padding=PaddingConfig(
            strategy=PaddingStrategy.INLINE_COMBINATIONAL,
            length_handling=LengthHandling.DESCRIPTOR_BASED,
            supports_partial_blocks=True,
        ),
        io=IOConfig(
            interface_style=InterfaceStyle.DESCRIPTOR_STREAM,
            data_bus_bits=128 * engine_count,
            supports_backpressure=True,
            flow_control=FlowControlStyle.VALID_READY,
        ),
        security=SecurityConfig(
            side_channel_protection=SideChannelProtection.NONE,
            constant_time_control=True,
            clear_state_on_done=True,
        ),
        rtl=RtlConfig(language=RtlLanguage.SYSTEMVERILOG, reset_style=ResetStyle.ASYNC_ACTIVE_LOW),
        description=(
            "FPGA architecture with N independent ASCON engines. Area scales roughly with N; "
            "throughput should scale close to linearly for independent messages if memory/I/O can feed all engines."
        ),
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
    return replace(config, name=f"{config.name}_{suffix}", datapath=datapath, io=io)


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
