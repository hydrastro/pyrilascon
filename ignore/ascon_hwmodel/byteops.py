from dataclasses import dataclass
from typing import Sequence

from ascon_hwmodel.bitstring import BitString, ParsedBitString, pad_bitstring, parse_bitstring
from ascon_hwmodel.uint import U64


@dataclass(frozen=True, slots=True)
class WordBytes64:
    """Exactly eight bytes that represent one Ascon 64-bit word in memory order."""

    data: bytes

    def __post_init__(self) -> None:
        if len(self.data) != 8:
            raise ValueError(f"WordBytes64 requires exactly 8 bytes, got {len(self.data)}")

    @classmethod
    def from_u64(cls, word: U64) -> "WordBytes64":
        return cls(word.value.to_bytes(8, "little"))

    def to_u64(self) -> U64:
        return U64(int.from_bytes(self.data, "little"))

    def to_bitstring(self) -> BitString:
        return BitString.from_bytes(self.data)


@dataclass(frozen=True, slots=True)
class ParsedBytes:
    """Byte-oriented view of parse(X, r) for byte-aligned rates."""

    full_blocks: tuple[bytes, ...]
    final_block: bytes
    rate_bytes: int

    def padded_final_block(self) -> bytes:
        return pad_bytes(self.final_block, self.rate_bytes)


def bytes_to_u64_le(data: bytes) -> U64:
    if len(data) != 8:
        raise ValueError(f"bytes_to_u64_le requires exactly 8 bytes, got {len(data)}")
    return U64(int.from_bytes(data, "little"))


def u64_to_bytes_le(word: U64) -> bytes:
    return word.value.to_bytes(8, "little")


def bytes_to_words64_le(data: bytes) -> tuple[U64, ...]:
    if len(data) % 8 != 0:
        raise ValueError(f"length must be a multiple of 8 bytes, got {len(data)}")
    return tuple(bytes_to_u64_le(data[index : index + 8]) for index in range(0, len(data), 8))


def words64_to_bytes_le(words: Sequence[U64]) -> bytes:
    return b"".join(u64_to_bytes_le(word) for word in words)


def parse_bytes(data: bytes, rate_bytes: int) -> ParsedBytes:
    """Byte-oriented specialization of Algorithm 1 parse(X, r)."""
    if not isinstance(rate_bytes, int):
        raise TypeError("rate_bytes must be int")
    if rate_bytes <= 0:
        raise ValueError("rate_bytes must be positive")
    full_count: int = len(data) // rate_bytes
    full_blocks: list[bytes] = []
    for block_index in range(full_count):
        start: int = block_index * rate_bytes
        full_blocks.append(data[start : start + rate_bytes])
    final_start: int = full_count * rate_bytes
    return ParsedBytes(tuple(full_blocks), data[final_start:], rate_bytes)


def pad_bytes(data: bytes, rate_bytes: int) -> bytes:
    """Byte-aligned Ascon padding.

    Since Ascon byte strings are interpreted LSB-first within each byte,
    appending the padding bit 1 at a byte boundary appends byte 0x01,
    followed by zero bytes until a complete rate block is formed.
    """
    if not isinstance(rate_bytes, int):
        raise TypeError("rate_bytes must be int")
    if rate_bytes <= 0:
        raise ValueError("rate_bytes must be positive")
    if len(data) >= rate_bytes:
        raise ValueError("pad_bytes expects the final partial block, not a full message")
    zero_count: int = rate_bytes - len(data) - 1
    return data + b"\x01" + (b"\x00" * zero_count)


def parse_bytes_as_bits(data: bytes, rate_bits: int) -> ParsedBitString:
    return parse_bitstring(BitString.from_bytes(data), rate_bits)


def pad_bytes_as_bits(data: bytes, rate_bits: int) -> BitString:
    return pad_bitstring(BitString.from_bytes(data), rate_bits)


def emit_verilog_pad64_partial_function() -> str:
    """Emit a byte-oriented pad helper for a partial 64-bit block.

    valid_bytes is 0..7. The data input is already little-endian in the lower bytes.
    """
    return "\n".join(
        (
            "function [63:0] ascon_pad64_partial;",
            "  input [63:0] data;",
            "  input [2:0]  valid_bytes;",
            "  begin",
            "    ascon_pad64_partial = data ^ (64'h0000_0000_0000_0001 << (valid_bytes * 8));",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_pad128_partial_function() -> str:
    """Emit a byte-oriented pad helper for a partial 128-bit block.

    valid_bytes is 0..15. The data input is already little-endian in the lower bytes.
    """
    return "\n".join(
        (
            "function [127:0] ascon_pad128_partial;",
            "  input [127:0] data;",
            "  input [3:0]   valid_bytes;",
            "  begin",
            "    ascon_pad128_partial = data ^ (128'h0000_0000_0000_0000_0000_0000_0000_0001 << (valid_bytes * 8));",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_aux_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon byte-oriented auxiliary helpers.",
            emit_verilog_pad64_partial_function(),
            emit_verilog_pad128_partial_function(),
        )
    )
