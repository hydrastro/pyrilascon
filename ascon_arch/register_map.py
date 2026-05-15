from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Register:
    name: str
    offset: int
    access: str
    description: str


@dataclass(frozen=True, slots=True)
class BitDef:
    name: str
    bit: int
    description: str


@dataclass(frozen=True, slots=True)
class EnumDef:
    name: str
    value: int
    description: str


REGISTER_MAP_VERSION: Final[int] = 1
REGISTER_WORD_BYTES: Final[int] = 4

REGISTERS: Final[tuple[Register, ...]] = (
    Register("CONTROL", 0x00, "RW", "Command register. Write START to launch an operation; write CLEAR to reset/clear status."),
    Register("STATUS", 0x04, "RO", "Status register."),
    Register("MODE", 0x08, "RW", "Selected algorithm/mode identifier."),
    Register("CAPABILITIES", 0x0C, "RO", "Hardware feature bitmap."),
    Register("AD_LEN", 0x10, "RW", "Associated-data length in bytes."),
    Register("TEXT_LEN", 0x14, "RW", "Plaintext/ciphertext/message length in bytes."),
    Register("OUT_LEN", 0x18, "RW", "Requested output length in bytes for hash/XOF/CXOF modes."),
    Register("CUSTOM_LEN", 0x1C, "RW", "Customization-string length in bytes for CXOF-like modes."),
    Register("KEY0", 0x20, "RW", "Key word 0, little-endian bytes 0..3."),
    Register("KEY1", 0x24, "RW", "Key word 1, little-endian bytes 4..7."),
    Register("KEY2", 0x28, "RW", "Key word 2, little-endian bytes 8..11."),
    Register("KEY3", 0x2C, "RW", "Key word 3, little-endian bytes 12..15."),
    Register("NONCE0", 0x30, "RW", "Nonce word 0, little-endian bytes 0..3."),
    Register("NONCE1", 0x34, "RW", "Nonce word 1, little-endian bytes 4..7."),
    Register("NONCE2", 0x38, "RW", "Nonce word 2, little-endian bytes 8..11."),
    Register("NONCE3", 0x3C, "RW", "Nonce word 3, little-endian bytes 12..15."),
    Register("DATA_IN", 0x40, "WO", "Input data word, little-endian byte order."),
    Register("DATA_IN_CTRL", 0x44, "WO", "Input stream control: valid, last, kind, and byte keep mask."),
    Register("DATA_OUT", 0x48, "RO", "Output data word, little-endian byte order."),
    Register("DATA_OUT_CTRL", 0x4C, "RO", "Output stream control: valid, last, and byte keep mask."),
    Register("TAG0", 0x60, "RW", "Tag word 0. Encryption reads generated tag; decryption writes expected tag."),
    Register("TAG1", 0x64, "RW", "Tag word 1. Encryption reads generated tag; decryption writes expected tag."),
    Register("TAG2", 0x68, "RW", "Tag word 2. Encryption reads generated tag; decryption writes expected tag."),
    Register("TAG3", 0x6C, "RW", "Tag word 3. Encryption reads generated tag; decryption writes expected tag."),
    Register("CYCLE_COUNT_LO", 0x70, "RO", "Low 32 bits of implementation-defined cycle counter for benchmarking."),
    Register("CYCLE_COUNT_HI", 0x74, "RO", "High 32 bits of implementation-defined cycle counter for benchmarking."),
    Register("ERROR_CODE", 0x78, "RO", "Implementation-defined error code."),
    Register("ABI_VERSION", 0x7C, "RO", "Register-map ABI version. Current value is 1."),
)

CONTROL_BITS: Final[tuple[BitDef, ...]] = (
    BitDef("START", 0, "Start the configured operation."),
    BitDef("DECRYPT", 1, "AEAD operation is decryption when set, encryption when clear."),
    BitDef("HASH", 2, "Operation is hash-like."),
    BitDef("XOF", 3, "Operation is XOF-like."),
    BitDef("CXOF", 4, "Operation uses customization input."),
    BitDef("CLEAR", 8, "Clear/reset the accelerator local state and sticky status."),
    BitDef("IRQ_ENABLE", 16, "Enable interrupt generation, if implemented."),
)

STATUS_BITS: Final[tuple[BitDef, ...]] = (
    BitDef("BUSY", 0, "Accelerator is processing."),
    BitDef("DONE", 1, "Operation completed."),
    BitDef("TAG_VALID", 2, "Decryption tag verification succeeded."),
    BitDef("ERROR", 3, "Operation failed."),
    BitDef("IN_READY", 4, "Input stream can accept a DATA_IN word."),
    BitDef("OUT_VALID", 5, "DATA_OUT contains a valid output word."),
)

DATA_CTRL_BITS: Final[tuple[BitDef, ...]] = (
    BitDef("LAST", 0, "This is the final word of this input stream segment."),
    BitDef("VALID", 1, "DATA_IN is valid."),
    BitDef("AD", 2, "Input word belongs to associated data."),
    BitDef("TEXT", 3, "Input word belongs to plaintext/ciphertext/message."),
    BitDef("CUSTOM", 4, "Input word belongs to CXOF customization data."),
)

DATA_KEEP_SHIFT: Final[int] = 8
DATA_KEEP_MASK: Final[int] = 0xF

MODE_ENUMS: Final[tuple[EnumDef, ...]] = (
    EnumDef("AEAD128", 0, "NIST Ascon-AEAD128."),
    EnumDef("AEAD128A", 1, "Legacy Ascon-128a placeholder."),
    EnumDef("AEAD128PQ", 2, "Legacy/post-quantum-style placeholder."),
    EnumDef("HASH", 3, "Ascon-Hash256."),
    EnumDef("HASHA", 4, "Hasha placeholder."),
    EnumDef("XOF", 5, "Ascon-XOF128."),
    EnumDef("XOFA", 6, "XOFa placeholder."),
    EnumDef("CXOF128", 7, "Ascon-CXOF128."),
)

CAPABILITY_BITS: Final[tuple[BitDef, ...]] = (
    BitDef("AEAD128", 0, "Ascon-AEAD128 is implemented."),
    BitDef("AEAD128A", 1, "Ascon-128a-compatible mode is implemented."),
    BitDef("AEAD128PQ", 2, "Ascon-128pq-compatible mode is implemented."),
    BitDef("HASH", 3, "Hash mode is implemented."),
    BitDef("HASHA", 4, "Hasha mode is implemented."),
    BitDef("XOF", 5, "XOF mode is implemented."),
    BitDef("XOFA", 6, "XOFa mode is implemented."),
    BitDef("CXOF128", 7, "CXOF128 mode is implemented."),
    BitDef("DECRYPT_BUFFERED", 16, "Plaintext release is buffered until tag verification succeeds."),
    BitDef("CONSTTIME_TAG_COMPARE", 17, "Tag comparison is intended to be constant-time."),
    BitDef("RAND_COUNTER_HARDENING", 18, "Control counters include randomization/hardening, if randomness is supplied."),
    BitDef("FAULT_DETECTION", 19, "Fault-detection mechanism is implemented."),
    BitDef("STREAMING_BYTEMASK", 20, "Input stream supports final-byte keep mask."),
    BitDef("CYCLE_COUNTER", 21, "Cycle counter registers are implemented."),
)

ERROR_ENUMS: Final[tuple[EnumDef, ...]] = (
    EnumDef("NONE", 0, "No error."),
    EnumDef("UNSUPPORTED_MODE", 1, "Selected mode is not implemented by this hardware instance."),
    EnumDef("BAD_LENGTH", 2, "Unsupported or inconsistent length fields."),
    EnumDef("STREAM_PROTOCOL", 3, "Input/output stream protocol violation."),
    EnumDef("TAG_INVALID", 4, "AEAD decryption tag mismatch."),
    EnumDef("FAULT_DETECTED", 5, "Fault-detection logic detected an inconsistency."),
)


def define_name(prefix: str, name: str) -> str:
    return f"{prefix}_{name}"
