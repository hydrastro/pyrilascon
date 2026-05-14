from dataclasses import dataclass
from typing import ClassVar, Sequence

from ascon_hwmodel.byteops import bytes_to_words64_le, words64_to_bytes_le
from ascon_hwmodel.uint import U64, U320


@dataclass(frozen=True, slots=True)
class AsconState:
    """Ascon 320-bit state represented as five 64-bit integer words.

    The logical Ascon bit order is little-endian:
        S[0:63]     is x0/S0
        S[64:127]   is x1/S1
        S[128:191]  is x2/S2
        S[192:255]  is x3/S3
        S[256:319]  is x4/S4

    When the state is represented as a Python integer or Verilog vector [319:0],
    the bit index is preserved: x0 occupies bits [63:0], and x4 occupies bits
    [319:256]. Therefore a Verilog concatenation is {x4, x3, x2, x1, x0}.
    """

    x0: U64
    x1: U64
    x2: U64
    x3: U64
    x4: U64

    WORD_COUNT: ClassVar[int] = 5
    WIDTH: ClassVar[int] = 320

    @classmethod
    def zero(cls) -> "AsconState":
        z: U64 = U64(0)
        return cls(z, z, z, z, z)

    @classmethod
    def from_words(cls, words: Sequence[U64]) -> "AsconState":
        if len(words) != cls.WORD_COUNT:
            raise ValueError(f"AsconState requires exactly {cls.WORD_COUNT} words")
        return cls(words[0], words[1], words[2], words[3], words[4])

    @classmethod
    def from_u320(cls, value: U320) -> "AsconState":
        """Load from a logical little-endian 320-bit integer/vector."""
        mask: int = (1 << U64.WIDTH) - 1
        return cls(
            U64(value.value & mask),
            U64((value.value >> 64) & mask),
            U64((value.value >> 128) & mask),
            U64((value.value >> 192) & mask),
            U64((value.value >> 256) & mask),
        )

    @classmethod
    def from_int(cls, value: int) -> "AsconState":
        return cls.from_u320(U320(value))

    @classmethod
    def from_bytes(cls, data: bytes) -> "AsconState":
        """Load five 64-bit words from a 40-byte state image in little-endian order."""
        if len(data) != 40:
            raise ValueError(f"AsconState byte image must be 40 bytes, got {len(data)}")
        return cls.from_words(bytes_to_words64_le(data))

    def words(self) -> tuple[U64, U64, U64, U64, U64]:
        return (self.x0, self.x1, self.x2, self.x3, self.x4)

    def word(self, index: int) -> U64:
        if index < 0 or index >= self.WORD_COUNT:
            raise IndexError(f"AsconState word index must be 0..4, got {index}")
        return self.words()[index]

    def with_word(self, index: int, value: U64) -> "AsconState":
        words: list[U64] = list(self.words())
        if index < 0 or index >= self.WORD_COUNT:
            raise IndexError(f"AsconState word index must be 0..4, got {index}")
        words[index] = value
        return AsconState.from_words(words)

    def xor_word(self, index: int, value: U64) -> "AsconState":
        old: U64 = self.word(index)
        return self.with_word(index, U64(old.value ^ value.value))

    def to_u320(self) -> U320:
        """Return a logical little-endian 320-bit integer/vector."""
        value: int = (
            self.x0.value
            | (self.x1.value << 64)
            | (self.x2.value << 128)
            | (self.x3.value << 192)
            | (self.x4.value << 256)
        )
        return U320(value)

    def to_int(self) -> int:
        return self.to_u320().value

    def to_bytes(self) -> bytes:
        """Store five 64-bit state words as a 40-byte little-endian memory image."""
        return words64_to_bytes_le(self.words())

    def hex_words(self) -> tuple[str, str, str, str, str]:
        return (self.x0.hex(), self.x1.hex(), self.x2.hex(), self.x3.hex(), self.x4.hex())

    def verilog_concat(self) -> str:
        """Return a Verilog concatenation for a [319:0] bus with S[0] at bit 0."""
        return "{" + ", ".join(word.verilog_literal() for word in reversed(self.words())) + "}"

    @staticmethod
    def verilog_pack_expr(x0: str, x1: str, x2: str, x3: str, x4: str) -> str:
        """Return a Verilog expression that packs named words into a [319:0] bus."""
        return f"{{{x4}, {x3}, {x2}, {x1}, {x0}}}"

    @staticmethod
    def verilog_word_slice(index: int) -> str:
        """Return the Verilog slice for logical state word index 0..4."""
        if index < 0 or index >= AsconState.WORD_COUNT:
            raise IndexError(f"AsconState word index must be 0..4, got {index}")
        low: int = index * 64
        high: int = low + 63
        return f"state[{high}:{low}]"


def emit_verilog_state_pack_function() -> str:
    """Emit a state packer for a [319:0] bus where state[0] is Ascon S[0]."""
    return "\n".join(
        (
            "function [319:0] ascon_state_pack;",
            "  input [63:0] x0;",
            "  input [63:0] x1;",
            "  input [63:0] x2;",
            "  input [63:0] x3;",
            "  input [63:0] x4;",
            "  begin",
            "    // Logical Ascon mapping: x0=state[63:0], x4=state[319:256]",
            f"    ascon_state_pack = {AsconState.verilog_pack_expr('x0', 'x1', 'x2', 'x3', 'x4')};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_state_word_function() -> str:
    """Emit a Verilog-2001 accessor for logical Ascon state words."""
    return "\n".join(
        (
            "function [63:0] ascon_state_word;",
            "  input [319:0] state;",
            "  input [2:0]   index;",
            "  begin",
            "    case (index)",
            f"      3'd0: ascon_state_word = {AsconState.verilog_word_slice(0)};",
            f"      3'd1: ascon_state_word = {AsconState.verilog_word_slice(1)};",
            f"      3'd2: ascon_state_word = {AsconState.verilog_word_slice(2)};",
            f"      3'd3: ascon_state_word = {AsconState.verilog_word_slice(3)};",
            f"      3'd4: ascon_state_word = {AsconState.verilog_word_slice(4)};",
            "      default: ascon_state_word = 64'h0000_0000_0000_0000;",
            "    endcase",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_state_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon state helpers. Include inside a module or package scope.",
            emit_verilog_state_pack_function(),
            emit_verilog_state_word_function(),
        )
    )
