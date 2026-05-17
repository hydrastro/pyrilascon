from enum import Enum


class TargetTechnology(str, Enum):
    ASIC = "asic"
    FPGA = "fpga"


class ArchitectureFamily(str, Enum):
    SHARED_DATAPATH = "shared_datapath"
    SEPARATE_ENC_DEC_DATAPATHS = "separate_enc_dec_datapaths"
    SHARED_PERMUTATION_MODE_FSM = "shared_permutation_mode_fsm"
    PARALLEL_ENGINES = "parallel_engines"




class TopLevelProfile(str, Enum):
    SINGLE_CORE = "single_core"
    DUAL_ENC_DEC_CORES = "dual_enc_dec_cores"
    N_IDENTICAL_AEAD_CORES = "n_identical_aead_cores"
    ONE_PIPELINED_PERMUTATION_N_CONTEXTS = "one_pipelined_permutation_n_contexts"
    M_PIPELINES_N_CONTEXTS = "m_pipelines_n_contexts"


class EngineCapability(str, Enum):
    AEAD_ENCRYPT_ONLY = "aead_encrypt_only"
    AEAD_DECRYPT_ONLY = "aead_decrypt_only"
    AEAD_ENCRYPT_DECRYPT = "aead_encrypt_decrypt"
    AEAD_HASH_XOF = "aead_hash_xof"


class AlgorithmFeature(str, Enum):
    # NIST SP 800-232 family currently implemented in the golden model.
    AEAD128 = "aead128"
    HASH256 = "hash256"
    XOF128 = "xof128"
    CXOF128 = "cxof128"

    # Architecture-level placeholders for broader design-space exploration.
    # These require dedicated golden-model/KAT support before they should be
    # considered production-verified algorithm targets.
    AEAD128A = "aead128a"
    AEAD80PQ = "aead80pq"
    HASH = "hash"
    HASHA = "hasha"
    XOF = "xof"
    XOFA = "xofa"
    CXOF = "cxof"

    # Backward-compatible legacy names kept for existing configs/tests.
    LEGACY_AEAD128A = "legacy_aead128a"
    LEGACY_AEAD80PQ = "legacy_aead80pq"
    LEGACY_AEAD128PQ = "legacy_aead128pq"


class PermutationStyle(str, Enum):
    ROUND_SERIAL = "round_serial"
    ROUND_UNROLLED = "round_unrolled"
    FULLY_UNROLLED = "fully_unrolled"
    ROUND_PIPELINED = "round_pipelined"
    FULLY_UNROLLED_PIPELINED = "fully_unrolled_pipelined"
    COLUMN_SERIAL = "column_serial"
    BIT_SERIAL = "bit_serial"


class PermutationProfile(str, Enum):
    ONE_ROUND_PER_CYCLE = "one_round_per_cycle"
    TWO_ROUNDS_PER_CYCLE = "two_rounds_per_cycle"
    FOUR_ROUNDS_PER_CYCLE = "four_rounds_per_cycle"
    EIGHT_ROUNDS_PER_CYCLE = "eight_rounds_per_cycle"
    FULLY_PIPELINED = "fully_pipelined"
    COLUMN_SERIAL = "column_serial"
    BIT_SERIAL = "bit_serial"


class SBoxStyle(str, Enum):
    BOOLEAN = "boolean"
    LUT5 = "lut5"
    CASE_TABLE = "case_table"
    MASKED = "masked"


class DatapathWidth(str, Enum):
    W1 = "1"
    W5 = "5"
    W8 = "8"
    W16 = "16"
    W32 = "32"
    W64 = "64"
    W128 = "128"
    W320 = "320"

    def bits(self) -> int:
        return int(self.value)


class DatapathProfile(str, Enum):
    W128 = "128_bit"
    W64 = "64_bit"
    W32 = "32_bit"
    W16 = "16_bit"
    W8_SERIAL = "8_bit_serial"
    W1_BIT_SERIAL = "1_bit_serial"
    W5_SBOX_SERIAL = "5bit_sbox_serial"


class StateStorageStyle(str, Enum):
    SINGLE_CONTEXT_REGS = "single_context_regs"
    STATE_PLUS_SHADOW_REGS = "state_plus_shadow_regs"
    MULTI_CONTEXT_REGFILE = "multi_context_regfile"
    FPGA_BRAM_CONTEXT_MEMORY = "fpga_bram_context_memory"
    FPGA_LUTRAM_CONTEXT_MEMORY = "fpga_lutram_context_memory"
    ASIC_SRAM_CONTEXT_MEMORY = "asic_sram_context_memory"
    SEPARATE_STATE_PER_CORE = "separate_state_per_core"
    SHARED_STATE_RAM_PIPELINED_P8 = "shared_state_ram_pipelined_p8"


class ContextProfile(str, Enum):
    SINGLE_320_REGISTER = "single_320_register"
    STATE_PLUS_SHADOW = "state_plus_shadow"
    MULTI_CONTEXT_REGISTERS = "multi_context_registers"
    FPGA_BRAM_LUTRAM = "fpga_bram_lutram"
    SEPARATE_STATE_PER_CORE = "separate_state_per_core"
    SHARED_STATE_RAM_PIPELINED_P8 = "shared_state_ram_pipelined_p8"


class ContextSchedulingStyle(str, Enum):
    SINGLE_CONTEXT = "single_context"
    STATIC_INTERLEAVED = "static_interleaved"
    DYNAMIC_QUEUE = "dynamic_queue"




class ControlProfile(str, Enum):
    HARDCODED_FSM = "hardcoded_fsm"
    MICROCODED_SEQUENCER = "microcoded_sequencer"
    COMMAND_FIFO = "command_fifo"
    AXI_STREAM = "axi_stream"
    AXI_STREAM_MICROCODED_HYBRID = "axi_stream_microcoded_hybrid"
    CSR_REGISTER_FILE = "csr_register_file"
    DMA_FED = "dma_fed"

class PaddingProfile(str, Enum):
    RTL_PERFORMED = "rtl_performed"
    FULL_ARBITRARY_BYTELENGTH = "full_arbitrary_bytelength"
    STREAMING_FINAL_BYTEMASK = "streaming_final_bytemask"


class PaddingStrategy(str, Enum):
    INLINE_COMBINATIONAL = "inline_combinational"
    FSM_ASSISTED = "fsm_assisted"
    PREPROCESSOR = "preprocessor"


class LengthHandling(str, Enum):
    EXTERNAL_LAST_STROBE = "external_last_strobe"
    INTERNAL_BYTE_COUNTER = "internal_byte_counter"
    DESCRIPTOR_BASED = "descriptor_based"
    STREAMING_FINAL_BYTEMASK = "streaming_final_bytemask"


class InterfaceStyle(str, Enum):
    BLOCK = "block"
    STREAM = "stream"
    DESCRIPTOR_STREAM = "descriptor_stream"


class FlowControlStyle(str, Enum):
    VALID_READY = "valid_ready"
    VALID_ONLY = "valid_only"
    FIFO_COUPLED = "fifo_coupled"


class DecryptionReleasePolicy(str, Enum):
    BUFFER_UNTIL_TAG_VERIFY = "buffer_until_tag_verify"


class DecryptionBufferStorage(str, Enum):
    INTERNAL_FIFO = "internal_fifo"
    BRAM_FIFO = "bram_fifo"
    SRAM_FIFO = "sram_fifo"
    EXTERNAL_MEMORY = "external_memory"


class SecurityProfile(str, Enum):
    NONE = "none"
    ASIC_BASELINE = "asic_rand_counter_consttime_tag"
    FPGA_FAULT_DETECT = "fpga_fault_detect_rand_counter_consttime_tag"
    FIRST_ORDER_MASKED = "first_order_masked"
    THRESHOLD_SBOX = "threshold_sbox"
    DUPLICATE_COMPUTE = "duplicate_compute"


class FaultDetectionProfile(str, Enum):
    NONE = "none"
    DUPLICATE_COMPUTE = "duplicate_compute"
    CONTROL_FLOW_COUNTERS = "control_flow_counters"


class SideChannelProtection(str, Enum):
    NONE = "none"
    FIRST_ORDER_MASKING = "first_order_masking"
    THRESHOLD_IMPLEMENTATION = "threshold_implementation"
    DOMAIN_ORIENTED_MASKING = "domain_oriented_masking"


class ResetStyle(str, Enum):
    ASYNC_ACTIVE_LOW = "async_active_low"
    SYNC_ACTIVE_HIGH = "sync_active_high"
    SYNC_ACTIVE_LOW = "sync_active_low"


class RtlLanguage(str, Enum):
    VERILOG_2001 = "verilog_2001"
    SYSTEMVERILOG = "systemverilog"
