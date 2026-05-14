from ascon_arch.config import ImplementationConfig
from ascon_arch.algorithm_planning import (
    AEAD_FEATURES,
    CXOF_FEATURES,
    HASH_FEATURES,
    XOF_FEATURES,
)
from ascon_arch.enums import (
    AlgorithmFeature,
    ArchitectureFamily,
    ContextProfile,
    ContextSchedulingStyle,
    ControlProfile,
    DatapathProfile,
    DatapathWidth,
    DecryptionReleasePolicy,
    FaultDetectionProfile,
    InterfaceStyle,
    LengthHandling,
    PaddingProfile,
    PaddingStrategy,
    PermutationStyle,
    SecurityProfile,
    SideChannelProtection,
    StateStorageStyle,
    TargetTechnology,
    TopLevelProfile,
)


class ConfigValidationError(ValueError):
    pass


def validate_config(config: ImplementationConfig) -> None:
    topology = config.topology
    permutation = config.permutation
    datapath = config.datapath
    context = config.context
    padding = config.padding
    control = config.control
    security = config.security

    if not config.name:
        raise ConfigValidationError("config name must not be empty")
    if not config.name.replace("_", "").isalnum():
        raise ConfigValidationError("config name must contain only letters, numbers, and underscores")

    if topology.engine_count < 1:
        raise ConfigValidationError("engine_count must be >= 1")
    if topology.aead_core_count < 1:
        raise ConfigValidationError("aead_core_count must be >= 1")
    if topology.permutation_pipeline_count < 0:
        raise ConfigValidationError("permutation_pipeline_count must be >= 0")
    if topology.contexts_per_pipeline < 1:
        raise ConfigValidationError("contexts_per_pipeline must be >= 1")
    if topology.mode_fsm_count_per_engine < 1:
        raise ConfigValidationError("mode_fsm_count_per_engine must be >= 1")
    if topology.encrypt_datapaths_per_engine < 0 or topology.decrypt_datapaths_per_engine < 0:
        raise ConfigValidationError("datapath counts must be non-negative")

    if config.io.data_bus_bits < 1:
        raise ConfigValidationError("data_bus_bits must be >= 1")
    if config.io.data_bus_bits % 8 != 0:
        raise ConfigValidationError("data_bus_bits must be byte-aligned")
    if config.io.interface_style == InterfaceStyle.DESCRIPTOR_STREAM:
        if padding.length_handling not in (LengthHandling.DESCRIPTOR_BASED, LengthHandling.STREAMING_FINAL_BYTEMASK):
            raise ConfigValidationError("descriptor_stream requires descriptor_based or streaming_final_bytemask length handling")



    if control.microcode_words < 0 or control.command_fifo_depth < 0 or control.csr_register_count < 0:
        raise ConfigValidationError("control resource counts must be non-negative")
    if control.axi_stream_command_channels < 0:
        raise ConfigValidationError("axi_stream_command_channels must be non-negative")
    if control.profile == ControlProfile.HARDCODED_FSM:
        if control.supports_runtime_algorithm_select or control.supports_concurrent_modes or control.supports_dma:
            raise ConfigValidationError("hardcoded_fsm must not enable runtime algorithm select, concurrent modes, or DMA")
        if len(config.algorithm.features) > 1:
            raise ConfigValidationError("hardcoded_fsm is only valid for one fixed algorithm feature")
    if control.profile == ControlProfile.MICROCODED_SEQUENCER:
        if control.microcode_words <= 0:
            raise ConfigValidationError("microcoded_sequencer requires microcode_words > 0")
        if not control.supports_runtime_algorithm_select:
            raise ConfigValidationError("microcoded_sequencer should support runtime algorithm selection")
    if control.profile == ControlProfile.COMMAND_FIFO:
        if control.command_fifo_depth <= 0:
            raise ConfigValidationError("command_fifo requires command_fifo_depth > 0")
    if control.profile in (ControlProfile.AXI_STREAM, ControlProfile.AXI_STREAM_MICROCODED_HYBRID):
        if not config.io.supports_backpressure or config.io.flow_control.value != "valid_ready":
            raise ConfigValidationError("AXI-stream control requires valid/ready backpressure")
        if control.command_fifo_depth <= 0:
            raise ConfigValidationError("AXI-stream control requires a positive command FIFO depth")
        if control.axi_stream_command_channels < 1:
            raise ConfigValidationError("AXI-stream control requires at least one command/status stream channel")
    if control.profile == ControlProfile.AXI_STREAM_MICROCODED_HYBRID:
        if control.microcode_words <= 0:
            raise ConfigValidationError("AXI-stream microcoded hybrid requires microcode storage")
        if not control.scheduler_required:
            raise ConfigValidationError("AXI-stream microcoded hybrid requires a scheduler")
    if control.profile == ControlProfile.CSR_REGISTER_FILE:
        if control.csr_register_count <= 0:
            raise ConfigValidationError("CSR register file control requires csr_register_count > 0")
    if control.profile == ControlProfile.DMA_FED:
        if config.target != TargetTechnology.FPGA:
            raise ConfigValidationError("DMA-fed profile is currently reserved for FPGA/system wrappers")
        if not control.supports_dma or not control.supports_descriptors:
            raise ConfigValidationError("DMA-fed profile requires DMA and descriptor support")
        if padding.length_handling != LengthHandling.DESCRIPTOR_BASED:
            raise ConfigValidationError("DMA-fed profile requires descriptor-based length handling")
    if topology.top_level_profile in (TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS, TopLevelProfile.M_PIPELINES_N_CONTEXTS):
        if not control.scheduler_required:
            raise ConfigValidationError("context-interleaved pipeline topologies require a scheduler-capable control profile")
        if control.profile == ControlProfile.HARDCODED_FSM:
            raise ConfigValidationError("hardcoded_fsm cannot schedule interleaved pipeline contexts")

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
    if context.contexts_per_engine < 1:
        raise ConfigValidationError("contexts_per_engine must be >= 1")
    if context.interleave_depth < 1:
        raise ConfigValidationError("interleave_depth must be >= 1")
    if context.state_memory_read_ports < 1 or context.state_memory_write_ports < 1:
        raise ConfigValidationError("state memory must expose at least one read and one write port")
    if context.scheduling == ContextSchedulingStyle.SINGLE_CONTEXT and context.context_count != 1 and topology.family != ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS and context.storage != StateStorageStyle.SEPARATE_STATE_PER_CORE:
        raise ConfigValidationError("single_context scheduling requires one context unless separate datapaths/cores model independent single contexts")
    if context.scheduling != ContextSchedulingStyle.SINGLE_CONTEXT and context.context_count < 2:
        raise ConfigValidationError("interleaved/dynamic scheduling requires at least two contexts")
    if context.storage == StateStorageStyle.SINGLE_CONTEXT_REGS and context.context_count > 2:
        raise ConfigValidationError("single_context_regs should not be used for more than two contexts")
    if context.context_id_bits < 0:
        raise ConfigValidationError("context_id_bits must be non-negative")
    if context.context_count > 1 and (1 << context.context_id_bits) < context.context_count:
        raise ConfigValidationError("context_id_bits cannot address context_count")
    if context.profile == ContextProfile.SINGLE_320_REGISTER:
        if context.shadow_state or context.rollback_supported:
            raise ConfigValidationError("single_320_register profile must not enable shadow/rollback state")
        if context.interleave_depth != 1:
            raise ConfigValidationError("single_320_register profile requires interleave_depth=1")
    if context.profile == ContextProfile.STATE_PLUS_SHADOW:
        if not context.shadow_state or not context.rollback_supported:
            raise ConfigValidationError("state_plus_shadow profile requires shadow_state and rollback_supported")
    if context.profile in (ContextProfile.MULTI_CONTEXT_REGISTERS, ContextProfile.FPGA_BRAM_LUTRAM, ContextProfile.SHARED_STATE_RAM_PIPELINED_P8):
        if context.context_count < 2 or context.contexts_per_engine < 2:
            raise ConfigValidationError("multi-context profiles require at least two contexts per engine")
        if context.interleave_depth < 2:
            raise ConfigValidationError("multi-context profiles require interleave_depth >= 2")
    if context.profile == ContextProfile.FPGA_BRAM_LUTRAM:
        if config.target != TargetTechnology.FPGA:
            raise ConfigValidationError("fpga_bram_lutram context profile is only valid for FPGA targets")
        if context.storage not in (StateStorageStyle.FPGA_BRAM_CONTEXT_MEMORY, StateStorageStyle.FPGA_LUTRAM_CONTEXT_MEMORY):
            raise ConfigValidationError("fpga_bram_lutram profile requires FPGA BRAM or LUTRAM storage")
    if context.profile == ContextProfile.SEPARATE_STATE_PER_CORE:
        if context.context_count != topology.engine_count:
            raise ConfigValidationError("separate_state_per_core requires one context per engine/core")
    if context.profile == ContextProfile.SHARED_STATE_RAM_PIPELINED_P8:
        if context.storage != StateStorageStyle.SHARED_STATE_RAM_PIPELINED_P8:
            raise ConfigValidationError("shared_state_ram_pipelined_p8 profile requires matching storage style")

    if topology.top_level_profile == TopLevelProfile.SINGLE_CORE:
        if topology.aead_core_count != 1:
            raise ConfigValidationError("single_core profile requires aead_core_count=1")
        if topology.permutation_pipeline_count not in (0, 1):
            raise ConfigValidationError("single_core profile should not instantiate multiple permutation pipelines")

    if topology.top_level_profile == TopLevelProfile.DUAL_ENC_DEC_CORES:
        if topology.family != ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS:
            raise ConfigValidationError("dual_enc_dec_cores requires separate_enc_dec_datapaths topology")
        if topology.aead_core_count != 2:
            raise ConfigValidationError("dual_enc_dec_cores requires aead_core_count=2")
        if topology.encrypt_datapaths_per_engine != 1 or topology.decrypt_datapaths_per_engine != 1:
            raise ConfigValidationError("dual_enc_dec_cores requires one encrypt and one decrypt datapath")

    if topology.top_level_profile == TopLevelProfile.N_IDENTICAL_AEAD_CORES:
        if topology.family != ArchitectureFamily.PARALLEL_ENGINES:
            raise ConfigValidationError("n_identical_aead_cores requires parallel_engines topology")
        if topology.aead_core_count != topology.engine_count:
            raise ConfigValidationError("n_identical_aead_cores requires aead_core_count == engine_count")
        if topology.engine_count < 2:
            raise ConfigValidationError("n_identical_aead_cores requires at least two cores")

    if topology.top_level_profile == TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS:
        if config.target != TargetTechnology.FPGA:
            raise ConfigValidationError("one_pipelined_permutation_n_contexts is currently an FPGA target profile")
        if topology.permutation_pipeline_count != 1:
            raise ConfigValidationError("one_pipelined_permutation_n_contexts requires exactly one permutation pipeline")
        if topology.contexts_per_pipeline < 2:
            raise ConfigValidationError("one_pipelined_permutation_n_contexts requires at least two contexts per pipeline")
        if context.context_count < topology.contexts_per_pipeline:
            raise ConfigValidationError("context_count must cover contexts_per_pipeline")
        if permutation.pipeline_initiation_interval is None:
            raise ConfigValidationError("context-interleaved pipeline topologies require a pipelined permutation config")

    if topology.top_level_profile == TopLevelProfile.M_PIPELINES_N_CONTEXTS:
        if config.target != TargetTechnology.FPGA:
            raise ConfigValidationError("m_pipelines_n_contexts is currently an FPGA target profile")
        if topology.permutation_pipeline_count < 2:
            raise ConfigValidationError("m_pipelines_n_contexts requires at least two permutation pipelines")
        if topology.contexts_per_pipeline < 2:
            raise ConfigValidationError("m_pipelines_n_contexts requires at least two contexts per pipeline")
        if context.context_count < topology.permutation_pipeline_count * topology.contexts_per_pipeline:
            raise ConfigValidationError("context_count must cover pipeline_count * contexts_per_pipeline")
        if permutation.pipeline_initiation_interval is None:
            raise ConfigValidationError("multi-pipeline context topologies require a pipelined permutation config")


    if padding.final_bytemask_width < 0:
        raise ConfigValidationError("final_bytemask_width must be non-negative")
    if padding.partial_block_buffer_bytes < 1:
        raise ConfigValidationError("partial_block_buffer_bytes must be positive")
    if padding.profile == PaddingProfile.RTL_PERFORMED:
        if not padding.pad_in_core:
            raise ConfigValidationError("rtl_performed padding requires pad_in_core=True")
        if padding.final_bytemask:
            raise ConfigValidationError("rtl_performed padding should not require a final byte mask")
        if padding.length_handling not in (LengthHandling.INTERNAL_BYTE_COUNTER, LengthHandling.DESCRIPTOR_BASED):
            raise ConfigValidationError("rtl_performed padding requires internal_byte_counter or descriptor_based length handling")
    if padding.profile == PaddingProfile.FULL_ARBITRARY_BYTELENGTH:
        if not padding.supports_arbitrary_byte_lengths:
            raise ConfigValidationError("full_arbitrary_bytelength profile must support arbitrary byte lengths")
        if not padding.requires_total_length:
            raise ConfigValidationError("full_arbitrary_bytelength profile requires an explicit total length")
        if padding.length_handling != LengthHandling.DESCRIPTOR_BASED:
            raise ConfigValidationError("full_arbitrary_bytelength profile requires descriptor_based length handling")
    if padding.profile == PaddingProfile.STREAMING_FINAL_BYTEMASK:
        if not padding.final_bytemask:
            raise ConfigValidationError("streaming_final_bytemask profile requires final_bytemask=True")
        if padding.final_bytemask_width < 1:
            raise ConfigValidationError("streaming_final_bytemask profile requires a positive final_bytemask_width")
        if padding.length_handling != LengthHandling.STREAMING_FINAL_BYTEMASK:
            raise ConfigValidationError("streaming_final_bytemask profile requires matching length handling")
        if not config.io.supports_backpressure or config.io.flow_control.value != "valid_ready":
            raise ConfigValidationError("streaming_final_bytemask is intended for valid/ready streaming interfaces")
        expected_keep_bits = max(1, config.io.data_bus_bits // 8)
        if padding.final_bytemask_width != expected_keep_bits:
            raise ConfigValidationError("final_bytemask_width must match data_bus_bits / 8")

    if padding.supports_bit_granular_lengths and padding.length_handling in (LengthHandling.EXTERNAL_LAST_STROBE, LengthHandling.STREAMING_FINAL_BYTEMASK):
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
        if permutation.context_interleaving_required and context.contexts_per_engine < max(2, min(permutation.pipeline_stages, 12)):
            raise ConfigValidationError("fully pipelined permutations require enough contexts per engine to fill the pipeline")

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

    if security.plaintext_buffer_capacity_bytes < 0:
        raise ConfigValidationError("plaintext_buffer_capacity_bytes must be non-negative")
    if config.algorithm.include_decrypt:
        if security.decryption_release_policy != DecryptionReleasePolicy.BUFFER_UNTIL_TAG_VERIFY:
            raise ConfigValidationError("decryption must buffer plaintext until the authentication tag verifies")
        if not security.plaintext_buffer_until_tag_verified:
            raise ConfigValidationError("decrypt plaintext release before tag verification is forbidden")
        if security.plaintext_buffer_capacity_bytes <= 0 and security.plaintext_buffer_storage.value != "external_memory":
            raise ConfigValidationError("safe decryption requires a positive plaintext buffer capacity unless using external memory")
        if not security.zeroize_plaintext_buffer_on_failure:
            raise ConfigValidationError("failed decryption must zeroize/drop the buffered plaintext")

    if security.profile == SecurityProfile.NONE:
        if security.fault_detection != FaultDetectionProfile.NONE:
            raise ConfigValidationError("security profile 'none' must not enable fault detection")
        if security.side_channel_protection != SideChannelProtection.NONE:
            raise ConfigValidationError("security profile 'none' must not enable side-channel protection")
        if security.constant_time_tag_compare or security.randomized_counter_hardening or security.duplicate_compute_check:
            raise ConfigValidationError("security profile 'none' must not enable countermeasures")

    if security.fault_detection == FaultDetectionProfile.DUPLICATE_COMPUTE and not security.duplicate_compute_check:
        raise ConfigValidationError("duplicate_compute fault detection requires duplicate_compute_check=True")
    if security.duplicate_compute_check and security.fault_detection != FaultDetectionProfile.DUPLICATE_COMPUTE:
        raise ConfigValidationError("duplicate_compute_check requires duplicate_compute fault detection profile")
    if security.profile == SecurityProfile.FPGA_FAULT_DETECT:
        if config.target != TargetTechnology.FPGA:
            raise ConfigValidationError("fpga_fault_detect profile is only valid for FPGA targets")
        if not security.constant_time_tag_compare or not security.randomized_counter_hardening:
            raise ConfigValidationError("fpga fault-detection baseline requires constant-time tag compare and randomized counter hardening")
        if security.fault_detection != FaultDetectionProfile.DUPLICATE_COMPUTE:
            raise ConfigValidationError("fpga fault-detection baseline requires duplicate computation")
    if security.profile == SecurityProfile.ASIC_BASELINE:
        if config.target != TargetTechnology.ASIC:
            raise ConfigValidationError("asic baseline security profile is only valid for ASIC targets")
        if not security.constant_time_tag_compare or not security.randomized_counter_hardening:
            raise ConfigValidationError("asic baseline requires constant-time tag compare and randomized counter hardening")
        if security.fault_detection != FaultDetectionProfile.NONE:
            raise ConfigValidationError("asic baseline chosen here does not enable duplicate-compute fault detection")

    if security.side_channel_protection != SideChannelProtection.NONE:
        if security.randomness_bits_per_cycle <= 0:
            raise ConfigValidationError("masked/side-channel-protected variants require randomness_bits_per_cycle > 0")
        if not padding.supports_partial_blocks:
            raise ConfigValidationError("side-channel-protected variants should keep partial block handling explicit")
    else:
        if security.randomness_bits_per_cycle != 0 and security.profile not in (SecurityProfile.FIRST_ORDER_MASKED, SecurityProfile.THRESHOLD_SBOX):
            raise ConfigValidationError("unmasked variants should not request randomness_bits_per_cycle")

    if security.profile == SecurityProfile.FIRST_ORDER_MASKED:
        if security.side_channel_protection != SideChannelProtection.FIRST_ORDER_MASKING:
            raise ConfigValidationError("first_order_masked profile requires first_order_masking protection")
    if security.profile == SecurityProfile.THRESHOLD_SBOX:
        if security.side_channel_protection != SideChannelProtection.THRESHOLD_IMPLEMENTATION:
            raise ConfigValidationError("threshold_sbox profile requires threshold_implementation protection")

    if not config.algorithm.features:
        raise ConfigValidationError("algorithm config must select at least one feature")
    if not any(feature in AEAD_FEATURES + HASH_FEATURES + XOF_FEATURES + CXOF_FEATURES for feature in config.algorithm.features):
        raise ConfigValidationError("algorithm config contains an unsupported feature")
    if not any(feature in config.algorithm.features for feature in AEAD_FEATURES) and (config.algorithm.include_encrypt or config.algorithm.include_decrypt):
        raise ConfigValidationError("encrypt/decrypt inclusion requires an AEAD feature")
    if config.algorithm.include_hash and not any(feature in config.algorithm.features for feature in HASH_FEATURES):
        raise ConfigValidationError("include_hash requires a hash-family feature")
    if config.algorithm.include_xof and not any(feature in config.algorithm.features for feature in XOF_FEATURES):
        raise ConfigValidationError("include_xof requires an XOF-family feature")
    if config.algorithm.include_cxof and not any(feature in config.algorithm.features for feature in CXOF_FEATURES):
        raise ConfigValidationError("include_cxof requires a CXOF-family feature")
