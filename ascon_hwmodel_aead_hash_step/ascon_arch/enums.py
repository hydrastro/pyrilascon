from enum import Enum


class TargetTechnology(str, Enum):
    ASIC = "asic"
    FPGA = "fpga"


class ArchitectureFamily(str, Enum):
    SHARED_DATAPATH = "shared_datapath"
    SEPARATE_ENC_DEC_DATAPATHS = "separate_enc_dec_datapaths"
    SHARED_PERMUTATION_MODE_FSM = "shared_permutation_mode_fsm"
    PARALLEL_ENGINES = "parallel_engines"


class EngineCapability(str, Enum):
    AEAD_ENCRYPT_ONLY = "aead_encrypt_only"
    AEAD_DECRYPT_ONLY = "aead_decrypt_only"
    AEAD_ENCRYPT_DECRYPT = "aead_encrypt_decrypt"
    AEAD_HASH_XOF = "aead_hash_xof"


class AlgorithmFeature(str, Enum):
    AEAD128 = "aead128"
    HASH256 = "hash256"
    XOF128 = "xof128"
    CXOF128 = "cxof128"


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
    W8 = "8"
    W16 = "16"
    W32 = "32"
    W64 = "64"
    W128 = "128"
    W320 = "320"

    def bits(self) -> int:
        return int(self.value)


class StateStorageStyle(str, Enum):
    SINGLE_CONTEXT_REGS = "single_context_regs"
    MULTI_CONTEXT_REGFILE = "multi_context_regfile"
    FPGA_BRAM_CONTEXT_MEMORY = "fpga_bram_context_memory"
    ASIC_SRAM_CONTEXT_MEMORY = "asic_sram_context_memory"


class ContextSchedulingStyle(str, Enum):
    SINGLE_CONTEXT = "single_context"
    STATIC_INTERLEAVED = "static_interleaved"
    DYNAMIC_QUEUE = "dynamic_queue"


class PaddingStrategy(str, Enum):
    INLINE_COMBINATIONAL = "inline_combinational"
    FSM_ASSISTED = "fsm_assisted"
    PREPROCESSOR = "preprocessor"


class LengthHandling(str, Enum):
    EXTERNAL_LAST_STROBE = "external_last_strobe"
    INTERNAL_BYTE_COUNTER = "internal_byte_counter"
    DESCRIPTOR_BASED = "descriptor_based"


class InterfaceStyle(str, Enum):
    BLOCK = "block"
    STREAM = "stream"
    DESCRIPTOR_STREAM = "descriptor_stream"


class FlowControlStyle(str, Enum):
    VALID_READY = "valid_ready"
    VALID_ONLY = "valid_only"
    FIFO_COUPLED = "fifo_coupled"


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
