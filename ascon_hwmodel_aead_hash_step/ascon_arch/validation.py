from ascon_arch.config import ImplementationConfig
from ascon_arch.enums import ArchitectureFamily, PermutationStyle, SideChannelProtection, TargetTechnology


class ConfigValidationError(ValueError):
    pass


def validate_config(config: ImplementationConfig) -> None:
    topology = config.topology
    permutation = config.permutation

    if not config.name:
        raise ConfigValidationError("config name must not be empty")
    if topology.engine_count < 1:
        raise ConfigValidationError("engine_count must be >= 1")
    if topology.mode_fsm_count_per_engine < 1:
        raise ConfigValidationError("mode_fsm_count_per_engine must be >= 1")
    if config.io.data_bus_bits < 1:
        raise ConfigValidationError("data_bus_bits must be >= 1")
    if config.io.data_bus_bits % 8 != 0:
        raise ConfigValidationError("data_bus_bits must be byte-aligned")
    if permutation.rounds_per_cycle < 1:
        raise ConfigValidationError("rounds_per_cycle must be >= 1")
    if permutation.pipeline_stages < 0:
        raise ConfigValidationError("pipeline_stages must be >= 0")

    if topology.family == ArchitectureFamily.SHARED_DATAPATH:
        if not topology.shared_encrypt_decrypt_datapath:
            raise ConfigValidationError("shared_datapath family requires shared_encrypt_decrypt_datapath=True")
        if topology.expected_parallel_operations() != topology.engine_count:
            raise ConfigValidationError("shared_datapath should expose one operation per engine")

    if topology.family == ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS:
        if topology.shared_encrypt_decrypt_datapath:
            raise ConfigValidationError("separate_enc_dec_datapaths requires shared_encrypt_decrypt_datapath=False")
        if topology.encrypt_datapaths_per_engine < 1 or topology.decrypt_datapaths_per_engine < 1:
            raise ConfigValidationError("separate_enc_dec_datapaths requires at least one encrypt and one decrypt datapath")

    if topology.family == ArchitectureFamily.SHARED_PERMUTATION_MODE_FSM:
        if not topology.shared_permutation_per_engine:
            raise ConfigValidationError("shared_permutation_mode_fsm requires shared_permutation_per_engine=True")

    if topology.family == ArchitectureFamily.PARALLEL_ENGINES:
        if topology.engine_count < 2:
            raise ConfigValidationError("parallel_engines family requires engine_count >= 2")
        if config.target != TargetTechnology.FPGA:
            raise ConfigValidationError("parallel_engines is currently reserved for FPGA-style scaling")

    if config.target == TargetTechnology.ASIC and topology.family == ArchitectureFamily.PARALLEL_ENGINES:
        raise ConfigValidationError("ASIC target should not use the FPGA N-parallel-engine topology in this baseline")

    if permutation.style == PermutationStyle.FULLY_UNROLLED_PIPELINED and permutation.pipeline_stages < 1:
        raise ConfigValidationError("fully_unrolled_pipelined requires at least one pipeline stage")

    if permutation.style == PermutationStyle.ROUND_SERIAL and permutation.rounds_per_cycle != 1:
        raise ConfigValidationError("round_serial requires rounds_per_cycle=1")

    if config.security.side_channel_protection != SideChannelProtection.NONE:
        raise ConfigValidationError("masked/side-channel-protected variants are not enabled in the current generator skeleton")
