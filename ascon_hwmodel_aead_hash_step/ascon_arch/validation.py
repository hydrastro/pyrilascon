from ascon_arch.config import ImplementationConfig
from ascon_arch.enums import (
    AlgorithmFeature,
    ArchitectureFamily,
    ContextSchedulingStyle,
    DatapathProfile,
    DatapathWidth,
    InterfaceStyle,
    LengthHandling,
    PaddingStrategy,
    PermutationStyle,
    SideChannelProtection,
    StateStorageStyle,
    TargetTechnology,
)


class ConfigValidationError(ValueError):
    pass


def validate_config(config: ImplementationConfig) -> None:
    topology = config.topology
    permutation = config.permutation
    datapath = config.datapath
    context = config.context
    padding = config.padding

    if not config.name:
        raise ConfigValidationError("config name must not be empty")
    if not config.name.replace("_", "").isalnum():
        raise ConfigValidationError("config name must contain only letters, numbers, and underscores")

    if topology.engine_count < 1:
        raise ConfigValidationError("engine_count must be >= 1")
    if topology.mode_fsm_count_per_engine < 1:
        raise ConfigValidationError("mode_fsm_count_per_engine must be >= 1")
    if topology.encrypt_datapaths_per_engine < 0 or topology.decrypt_datapaths_per_engine < 0:
        raise ConfigValidationError("datapath counts must be non-negative")

    if config.io.data_bus_bits < 1:
        raise ConfigValidationError("data_bus_bits must be >= 1")
    if config.io.data_bus_bits % 8 != 0:
        raise ConfigValidationError("data_bus_bits must be byte-aligned")
    if config.io.interface_style == InterfaceStyle.DESCRIPTOR_STREAM:
        if padding.length_handling != LengthHandling.DESCRIPTOR_BASED:
            raise ConfigValidationError("descriptor_stream requires descriptor_based length handling")

    if permutation.rounds_per_cycle < 1:
        raise ConfigValidationError("rounds_per_cycle must be >= 1")
    if permutation.rounds_per_cycle > 12:
        raise ConfigValidationError("rounds_per_cycle must be <= 12")
    if permutation.pipeline_stages < 0:
        raise ConfigValidationError("pipeline_stages must be >= 0")
    if permutation.unroll_factor < 1 or permutation.unroll_factor > 12:
        raise ConfigValidationError("unroll_factor must satisfy 1 <= unroll_factor <= 12")
    if permutation.sbox_columns_per_cycle < 1 or permutation.sbox_columns_per_cycle > 64:
        raise ConfigValidationError("sbox_columns_per_cycle must satisfy 1 <= value <= 64")
    if permutation.pipeline_initiation_interval is not None and permutation.pipeline_initiation_interval < 1:
        raise ConfigValidationError("pipeline_initiation_interval must be positive when provided")

    if datapath.state_width_bits != 320:
        raise ConfigValidationError("ASCON state_width_bits must be 320")
    if datapath.key_width_bits != 128:
        raise ConfigValidationError("current generator supports only 128-bit AEAD keys")
    if datapath.tag_width_bits != 128:
        raise ConfigValidationError("current generator supports only 128-bit AEAD tags")
    if datapath.rate_width_bits not in (64, 128):
        raise ConfigValidationError("rate_width_bits must be 64 or 128")
    if datapath.lane_width.bits() not in (1, 5, 8, 16, 32, 64, 128, 320):
        raise ConfigValidationError("unsupported lane_width")
    if datapath.absorb_width.bits() not in (1, 8, 16, 32, 64, 128):
        raise ConfigValidationError("absorb_width must be 1, 8, 16, 32, 64, or 128")
    if datapath.io_word_width.bits() not in (1, 8, 16, 32, 64, 128):
        raise ConfigValidationError("io_word_width must be 1, 8, 16, 32, 64, or 128")
    if datapath.rate_width_bits % datapath.absorb_width.bits() != 0:
        raise ConfigValidationError("absorb_width must evenly divide rate_width_bits")
    if datapath.lane_width.bits() > datapath.state_width_bits:
        raise ConfigValidationError("lane_width must not exceed the 320-bit state")
    if datapath.absorb_width == DatapathWidth.W128 and datapath.rate_width_bits < 128:
        raise ConfigValidationError("128-bit absorb width requires a 128-bit rate")
    if datapath.profile == DatapathProfile.W5_SBOX_SERIAL and datapath.lane_width != DatapathWidth.W5:
        raise ConfigValidationError("5bit_sbox_serial profile requires lane_width=5")
    if datapath.profile == DatapathProfile.W1_BIT_SERIAL and datapath.lane_width != DatapathWidth.W1:
        raise ConfigValidationError("1_bit_serial profile requires lane_width=1")
    if datapath.profile == DatapathProfile.W8_SERIAL and datapath.lane_width != DatapathWidth.W8:
        raise ConfigValidationError("8_bit_serial profile requires lane_width=8")
    if datapath.lane_width.bits() < 64 and not datapath.serialized_state_update:
        raise ConfigValidationError("lane widths below 64 bits must set serialized_state_update=True")
    if datapath.absorb_width.bits() < 128 and not datapath.serialized_absorb:
        raise ConfigValidationError("absorb widths below 128 bits must set serialized_absorb=True")

    if context.context_count < 1:
        raise ConfigValidationError("context_count must be >= 1")
    if context.interleave_depth < 1:
        raise ConfigValidationError("interleave_depth must be >= 1")
    if context.scheduling == ContextSchedulingStyle.SINGLE_CONTEXT and context.context_count != 1 and topology.family != ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS:
        raise ConfigValidationError("single_context scheduling requires context_count=1 unless separate datapaths model separate contexts")
    if context.scheduling != ContextSchedulingStyle.SINGLE_CONTEXT and context.context_count < 2:
        raise ConfigValidationError("interleaved/dynamic scheduling requires at least two contexts")
    if context.storage == StateStorageStyle.SINGLE_CONTEXT_REGS and context.context_count > 2:
        raise ConfigValidationError("single_context_regs should not be used for more than two contexts")
    if context.context_id_bits < 0:
        raise ConfigValidationError("context_id_bits must be non-negative")
    if context.context_count > 1 and (1 << context.context_id_bits) < context.context_count:
        raise ConfigValidationError("context_id_bits cannot address context_count")

    if padding.supports_bit_granular_lengths and padding.length_handling == LengthHandling.EXTERNAL_LAST_STROBE:
        raise ConfigValidationError("bit-granular lengths require an internal counter or descriptor length field")
    if padding.strategy == PaddingStrategy.PREPROCESSOR and padding.length_handling == LengthHandling.INTERNAL_BYTE_COUNTER:
        raise ConfigValidationError("preprocessor padding should use external or descriptor length handling")

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
        if not config.io.separate_encrypt_decrypt_ports:
            raise ConfigValidationError("separate_enc_dec_datapaths should expose separate encrypt/decrypt ports")

    if topology.family == ArchitectureFamily.SHARED_PERMUTATION_MODE_FSM:
        if not topology.shared_permutation_per_engine:
            raise ConfigValidationError("shared_permutation_mode_fsm requires shared_permutation_per_engine=True")

    if topology.family == ArchitectureFamily.PARALLEL_ENGINES:
        if topology.engine_count < 2:
            raise ConfigValidationError("parallel_engines family requires engine_count >= 2")
        if config.target != TargetTechnology.FPGA:
            raise ConfigValidationError("parallel_engines is currently reserved for FPGA-style scaling")
        if context.context_count < topology.engine_count:
            raise ConfigValidationError("parallel_engines requires at least one context per engine")

    if config.target == TargetTechnology.ASIC and topology.family == ArchitectureFamily.PARALLEL_ENGINES:
        raise ConfigValidationError("ASIC target should not use the FPGA N-parallel-engine topology in this baseline")

    if permutation.style in (PermutationStyle.FULLY_UNROLLED_PIPELINED, PermutationStyle.ROUND_PIPELINED):
        if permutation.pipeline_stages < 1:
            raise ConfigValidationError("pipelined permutation requires at least one pipeline stage")
        if not permutation.register_between_rounds:
            raise ConfigValidationError("pipelined permutation requires register_between_rounds=True")
        if permutation.pipeline_initiation_interval is None:
            raise ConfigValidationError("pipelined permutation requires pipeline_initiation_interval")
        if permutation.context_interleaving_required and context.interleave_depth < 2 and topology.engine_count < 2:
            raise ConfigValidationError("interleaved pipeline requires multiple contexts or multiple engines")

    if permutation.style == PermutationStyle.ROUND_SERIAL:
        if permutation.rounds_per_cycle != 1:
            raise ConfigValidationError("round_serial requires rounds_per_cycle=1")
        if permutation.unroll_factor != 1:
            raise ConfigValidationError("round_serial requires unroll_factor=1")
        if permutation.sbox_columns_per_cycle != 64:
            raise ConfigValidationError("round_serial expects the full 64 S-box columns per round")

    if permutation.style == PermutationStyle.ROUND_UNROLLED:
        if permutation.rounds_per_cycle < 2:
            raise ConfigValidationError("round_unrolled requires rounds_per_cycle >= 2")
        if permutation.unroll_factor != permutation.rounds_per_cycle:
            raise ConfigValidationError("round_unrolled requires unroll_factor == rounds_per_cycle")
        if permutation.sbox_columns_per_cycle != 64:
            raise ConfigValidationError("round_unrolled expects the full 64 S-box columns per unrolled round")

    if permutation.style == PermutationStyle.COLUMN_SERIAL:
        if datapath.profile in (DatapathProfile.W128, DatapathProfile.W64) and datapath.lane_width.bits() == 128:
            raise ConfigValidationError("column_serial should not be paired with a 128-bit datapath profile")
        if datapath.lane_width.bits() > 64:
            raise ConfigValidationError("column_serial should use a narrow datapath lane")
        if permutation.sbox_columns_per_cycle >= 64:
            raise ConfigValidationError("column_serial should use fewer than 64 S-box columns per cycle")

    if permutation.style == PermutationStyle.BIT_SERIAL:
        if datapath.lane_width.bits() > 16:
            raise ConfigValidationError("bit_serial should use a very narrow datapath lane")
        if permutation.sbox_columns_per_cycle != 1:
            raise ConfigValidationError("bit_serial requires sbox_columns_per_cycle=1")

    if config.security.side_channel_protection != SideChannelProtection.NONE:
        if config.security.randomness_bits_per_cycle <= 0:
            raise ConfigValidationError("masked/side-channel-protected variants require randomness_bits_per_cycle > 0")
        if not padding.supports_partial_blocks:
            raise ConfigValidationError("side-channel-protected variants should keep partial block handling explicit")

    aead_like = (
        AlgorithmFeature.AEAD128,
        AlgorithmFeature.LEGACY_AEAD128A,
        AlgorithmFeature.LEGACY_AEAD128PQ,
    )
    if not any(feature in config.algorithm.features for feature in aead_like) and (config.algorithm.include_encrypt or config.algorithm.include_decrypt):
        raise ConfigValidationError("encrypt/decrypt inclusion requires an AEAD feature")
