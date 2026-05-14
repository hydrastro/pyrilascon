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


class PermutationStyle(str, Enum):
    ROUND_SERIAL = "round_serial"
    ROUND_UNROLLED = "round_unrolled"
    FULLY_UNROLLED = "fully_unrolled"
    FULLY_UNROLLED_PIPELINED = "fully_unrolled_pipelined"
    COLUMN_SERIAL = "column_serial"


class SBoxStyle(str, Enum):
    BOOLEAN = "boolean"
    LUT5 = "lut5"
    CASE_TABLE = "case_table"
    MASKED = "masked"


class InterfaceStyle(str, Enum):
    BLOCK = "block"
    STREAM = "stream"
    DESCRIPTOR_STREAM = "descriptor_stream"


class SideChannelProtection(str, Enum):
    NONE = "none"
    FIRST_ORDER_MASKING = "first_order_masking"
    THRESHOLD_IMPLEMENTATION = "threshold_implementation"
    DOMAIN_ORIENTED_MASKING = "domain_oriented_masking"
