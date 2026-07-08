from dataclasses import dataclass
from typing import ClassVar

from ascon_hwmodel.uint import U64, U128


@dataclass(frozen=True, slots=True)
class Block64:
    """A 64-bit rate block as an unsigned integer value.

    Byte conversion is always little-endian: byte 0 is integer bits [7:0].
    """

    value: U64

    WIDTH: ClassVar[int] = 64
    BYTE_LENGTH: ClassVar[int] = 8

    @classmethod
    def from_int(cls, value: int) -> "Block64":
        return cls(U64(value))

    @classmethod
    def from_bytes(cls, data: bytes) -> "Block64":
        if len(data) != cls.BYTE_LENGTH:
            raise ValueError(f"Block64 requires exactly 8 bytes, got {len(data)}")
        return cls(U64(int.from_bytes(data, "little")))

    def to_bytes(self) -> bytes:
        return self.value.value.to_bytes(self.BYTE_LENGTH, "little")

    def to_u64(self) -> U64:
        return self.value

    def hex(self) -> str:
        return self.value.hex()

    def verilog_literal(self) -> str:
        return self.value.verilog_literal()


@dataclass(frozen=True, slots=True)
class Block128:
    """A 128-bit rate/key/nonce/tag block as an unsigned integer value.

    The lower word is bits [63:0] and is loaded from bytes [0:8].
    The upper word is bits [127:64] and is loaded from bytes [8:16].
    """

    value: U128

    WIDTH: ClassVar[int] = 128
    BYTE_LENGTH: ClassVar[int] = 16

    @classmethod
    def from_int(cls, value: int) -> "Block128":
        return cls(U128(value))

    @classmethod
    def from_bytes(cls, data: bytes) -> "Block128":
        if len(data) != cls.BYTE_LENGTH:
            raise ValueError(f"Block128 requires exactly 16 bytes, got {len(data)}")
        return cls(U128(int.from_bytes(data, "little")))

    @classmethod
    def from_words(cls, low: U64, high: U64) -> "Block128":
        return cls(U128(low.value | (high.value << 64)))

    @property
    def low(self) -> U64:
        return U64(self.value.value & ((1 << 64) - 1))

    @property
    def high(self) -> U64:
        return U64((self.value.value >> 64) & ((1 << 64) - 1))

    def words(self) -> tuple[U64, U64]:
        return (self.low, self.high)

    def to_bytes(self) -> bytes:
        return self.value.value.to_bytes(self.BYTE_LENGTH, "little")

    def hex(self) -> str:
        return self.value.hex()

    def verilog_literal(self) -> str:
        return self.value.verilog_literal()


class Key128(Block128):
    """Semantic 128-bit AEAD key wrapper."""


class Nonce128(Block128):
    """Semantic 128-bit AEAD nonce wrapper."""


class Tag128(Block128):
    """Semantic 128-bit AEAD tag wrapper."""
