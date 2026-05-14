from typing import Final

from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64

MASK64: Final[int] = (1 << 64) - 1

SBOX: Final[tuple[int, ...]] = (
    0x04, 0x0B, 0x1F, 0x14, 0x1A, 0x15, 0x09, 0x02,
    0x1B, 0x05, 0x08, 0x12, 0x1D, 0x03, 0x06, 0x1C,
    0x1E, 0x13, 0x07, 0x0E, 0x00, 0x0D, 0x11, 0x18,
    0x10, 0x0C, 0x01, 0x19, 0x16, 0x0A, 0x0F, 0x17,
)


def sbox5_value(value: int) -> int:
    """Reference 5-bit S-box lookup.

    The input integer is interpreted as x0 x1 x2 x3 x4, where x0 is bit 4
    and x4 is bit 0. The output is encoded in the same order.
    """
    if value < 0 or value >= 32:
        raise ValueError("SBOX input must be a 5-bit integer")
    return SBOX[value]


def sbox5_bits(x0: int, x1: int, x2: int, x3: int, x4: int) -> tuple[int, int, int, int, int]:
    value: int = ((x0 & 1) << 4) | ((x1 & 1) << 3) | ((x2 & 1) << 2) | ((x3 & 1) << 1) | (x4 & 1)
    output: int = sbox5_value(value)
    return ((output >> 4) & 1, (output >> 3) & 1, (output >> 2) & 1, (output >> 1) & 1, output & 1)


def p_s_lut(state: AsconState) -> AsconState:
    """Reference substitution layer: 64 scalar 5-bit S-box table lookups.

    This is intentionally simple and mirrors the mathematical definition. It is
    useful as an oracle for tests, but it is not the preferred Python or RTL
    implementation style.
    """
    y: list[int] = [0, 0, 0, 0, 0]
    xs: tuple[U64, U64, U64, U64, U64] = state.words()
    for bit_index in range(64):
        input_value: int = 0
        for word_index, word in enumerate(xs):
            bit: int = (word.value >> bit_index) & 1
            input_value |= bit << (4 - word_index)
        output_value: int = sbox5_value(input_value)
        for word_index in range(5):
            bit = (output_value >> (4 - word_index)) & 1
            y[word_index] |= bit << bit_index
    return AsconState(U64(y[0]), U64(y[1]), U64(y[2]), U64(y[3]), U64(y[4]))


def p_s_bitsliced(state: AsconState) -> AsconState:
    """Hardware-shaped substitution layer using 64-bit boolean operations.

    This computes the same 64 parallel 5-bit S-box applications as p_s_lut(),
    but directly over the five 64-bit state words.
    """
    x0: int = state.x0.value
    x1: int = state.x1.value
    x2: int = state.x2.value
    x3: int = state.x3.value
    x4: int = state.x4.value

    y0: int = ((x4 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ (x1 & x0) ^ x1 ^ x0) & MASK64
    y1: int = (x4 ^ (x3 & x2) ^ (x3 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ x1 ^ x0) & MASK64
    y2: int = ((x4 & x3) ^ x4 ^ x2 ^ x1 ^ MASK64) & MASK64
    y3: int = ((x4 & x0) ^ x4 ^ (x3 & x0) ^ x3 ^ x2 ^ x1 ^ x0) & MASK64
    y4: int = ((x4 & x1) ^ x4 ^ x3 ^ (x1 & x0) ^ x1) & MASK64
    return AsconState(U64(y0), U64(y1), U64(y2), U64(y3), U64(y4))


def p_s(state: AsconState) -> AsconState:
    """Default substitution layer implementation used by the permutation."""
    return p_s_bitsliced(state)


def emit_verilog_sbox5_lut_function() -> str:
    lines: list[str] = [
        "function [4:0] ascon_sbox5_lut;",
        "  input [4:0] x;",
        "  begin",
        "    case (x)",
    ]
    for index, value in enumerate(SBOX):
        lines.append(f"      5'h{index:02X}: ascon_sbox5_lut = 5'h{value:02X};")
    lines.extend(
        (
            "      default: ascon_sbox5_lut = 5'h00;",
            "    endcase",
            "  end",
            "endfunction",
        )
    )
    return "\n".join(lines)


def emit_verilog_ps_bitsliced_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_p_s_bitsliced;",
            "  input [319:0] state;",
            "  reg [63:0] x0;",
            "  reg [63:0] x1;",
            "  reg [63:0] x2;",
            "  reg [63:0] x3;",
            "  reg [63:0] x4;",
            "  reg [63:0] y0;",
            "  reg [63:0] y1;",
            "  reg [63:0] y2;",
            "  reg [63:0] y3;",
            "  reg [63:0] y4;",
            "  begin",
            "    x0 = state[63:0];",
            "    x1 = state[127:64];",
            "    x2 = state[191:128];",
            "    x3 = state[255:192];",
            "    x4 = state[319:256];",
            "    y0 = (x4 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ (x1 & x0) ^ x1 ^ x0;",
            "    y1 = x4 ^ (x3 & x2) ^ (x3 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ x1 ^ x0;",
            "    y2 = (x4 & x3) ^ x4 ^ x2 ^ x1 ^ 64'hFFFF_FFFF_FFFF_FFFF;",
            "    y3 = (x4 & x0) ^ x4 ^ (x3 & x0) ^ x3 ^ x2 ^ x1 ^ x0;",
            "    y4 = (x4 & x1) ^ x4 ^ x3 ^ (x1 & x0) ^ x1;",
            "    ascon_p_s_bitsliced = {y4, y3, y2, y1, y0};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_ps_lut_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_p_s_lut;",
            "  input [319:0] state;",
            "  integer j;",
            "  reg [4:0] y;",
            "  reg [319:0] out;",
            "  begin",
            "    out = 320'b0;",
            "    for (j = 0; j < 64; j = j + 1) begin",
            "      y = ascon_sbox5_lut({state[j], state[64+j], state[128+j], state[192+j], state[256+j]});",
            "      out[j]       = y[4];",
            "      out[64+j]    = y[3];",
            "      out[128+j]   = y[2];",
            "      out[192+j]   = y[1];",
            "      out[256+j]   = y[0];",
            "    end",
            "    ascon_p_s_lut = out;",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_ps_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_p_s;",
            "  input [319:0] state;",
            "  begin",
            "    // Default RTL view: direct bitsliced boolean network.",
            "    ascon_p_s = ascon_p_s_bitsliced(state);",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_ps_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon substitution layer p_S.",
            emit_verilog_sbox5_lut_function(),
            emit_verilog_ps_lut_function(),
            emit_verilog_ps_bitsliced_function(),
            emit_verilog_ps_function(),
        )
    )
