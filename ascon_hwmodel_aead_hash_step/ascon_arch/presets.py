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
    ContextSchedulingStyle,
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
        datapath=DatapathConfig(
            lane_width=DatapathWidth.W64,
            absorb_width=DatapathWidth.W128,
            split_encrypt_decrypt_control=False,
            share_key_registers=True,
            share_pad_logic=True,
        ),
        context=ContextConfig(
            scheduling=ContextSchedulingStyle.SINGLE_CONTEXT,
            storage=StateStorageStyle.SINGLE_CONTEXT_REGS,
            context_count=1,
            interleave_depth=1,
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
        datapath=DatapathConfig(
            lane_width=DatapathWidth.W64,
            absorb_width=DatapathWidth.W128,
            split_encrypt_decrypt_control=True,
            share_key_registers=False,
            share_pad_logic=True,
        ),
        context=ContextConfig(
            scheduling=ContextSchedulingStyle.SINGLE_CONTEXT,
            storage=StateStorageStyle.SINGLE_CONTEXT_REGS,
            context_count=2,
            interleave_depth=1,
            context_id_bits=1,
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
        datapath=DatapathConfig(
            lane_width=DatapathWidth.W64,
            absorb_width=DatapathWidth.W128,
            split_encrypt_decrypt_control=False,
            share_key_registers=True,
            share_pad_logic=True,
        ),
        context=ContextConfig(),
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
        datapath=DatapathConfig(
            lane_width=DatapathWidth.W320,
            absorb_width=DatapathWidth.W128,
            split_encrypt_decrypt_control=True,
            share_key_registers=False,
            share_pad_logic=False,
        ),
        context=ContextConfig(
            scheduling=ContextSchedulingStyle.DYNAMIC_QUEUE,
            storage=StateStorageStyle.MULTI_CONTEXT_REGFILE,
            context_count=engine_count,
            interleave_depth=engine_count,
            context_id_bits=max(1, (engine_count - 1).bit_length()),
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
    narrow_datapath = replace(base.datapath, lane_width=DatapathWidth.W64)
    return replace(
        config_with_permutation_profile(
            base,
            PermutationProfile.COLUMN_SERIAL,
            name_suffix="column_serial",
            sbox_style=SBoxStyle.BOOLEAN,
        ),
        datapath=narrow_datapath,
    )


def fpga_n_parallel_engines_with_profile_config(engine_count: int, profile: PermutationProfile) -> ImplementationConfig:
    sbox = SBoxStyle.LUT5 if profile in (
        PermutationProfile.FOUR_ROUNDS_PER_CYCLE,
        PermutationProfile.EIGHT_ROUNDS_PER_CYCLE,
        PermutationProfile.FULLY_PIPELINED,
    ) else SBoxStyle.BOOLEAN
    base = fpga_n_parallel_engines_config(engine_count)
    return config_with_permutation_profile(base, profile, sbox_style=sbox)
