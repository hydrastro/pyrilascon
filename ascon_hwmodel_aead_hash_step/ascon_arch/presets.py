from ascon_arch.config import DatapathTopology, IOConfig, ImplementationConfig, PermutationConfig, SecurityConfig
from ascon_arch.enums import (
    ArchitectureFamily,
    EngineCapability,
    InterfaceStyle,
    PermutationStyle,
    SBoxStyle,
    SideChannelProtection,
    TargetTechnology,
)


def asic_two_datapaths_config() -> ImplementationConfig:
    """ASIC baseline chosen by the user: separate encryption and decryption datapaths."""
    return ImplementationConfig(
        name="asic_two_datapaths",
        target=TargetTechnology.ASIC,
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
        ),
        io=IOConfig(
            interface_style=InterfaceStyle.STREAM,
            data_bus_bits=128,
            supports_backpressure=True,
        ),
        security=SecurityConfig(
            side_channel_protection=SideChannelProtection.NONE,
            constant_time_control=True,
        ),
        description=(
            "ASIC architecture with independent AEAD encryption and decryption datapaths. "
            "This costs more area than a shared datapath but allows one encrypt and one decrypt operation to progress concurrently."
        ),
    )


def fpga_n_parallel_engines_config(engine_count: int) -> ImplementationConfig:
    """FPGA baseline chosen by the user: N independent parallel engines."""
    return ImplementationConfig(
        name=f"fpga_{engine_count}_parallel_engines",
        target=TargetTechnology.FPGA,
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
        permutation=PermutationConfig(
            style=PermutationStyle.FULLY_UNROLLED_PIPELINED,
            sbox_style=SBoxStyle.LUT5,
            rounds_per_cycle=12,
            pipeline_stages=12,
        ),
        io=IOConfig(
            interface_style=InterfaceStyle.STREAM,
            data_bus_bits=128 * engine_count,
            supports_backpressure=True,
        ),
        security=SecurityConfig(
            side_channel_protection=SideChannelProtection.NONE,
            constant_time_control=True,
        ),
        description=(
            "FPGA architecture with N independent ASCON engines. Area scales roughly with N; "
            "throughput should scale close to linearly for independent messages if memory/I/O can feed all engines."
        ),
    )
