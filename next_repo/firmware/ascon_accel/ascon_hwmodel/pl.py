from typing import Final

from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64

MASK64: Final[int] = (1 << 64) - 1


def rotr64(value: U64, amount: int) -> U64:
    if amount < 0 or amount >= 64:
        raise ValueError("rotation amount must satisfy 0 <= amount < 64")
    if amount == 0:
        return value
    x: int = value.value
    return U64(((x >> amount) | (x << (64 - amount))) & MASK64)


def sigma0(word: U64) -> U64:
    return U64(word.value ^ rotr64(word, 19).value ^ rotr64(word, 28).value)


def sigma1(word: U64) -> U64:
    return U64(word.value ^ rotr64(word, 61).value ^ rotr64(word, 39).value)


def sigma2(word: U64) -> U64:
    return U64(word.value ^ rotr64(word, 1).value ^ rotr64(word, 6).value)


def sigma3(word: U64) -> U64:
    return U64(word.value ^ rotr64(word, 10).value ^ rotr64(word, 17).value)


def sigma4(word: U64) -> U64:
    return U64(word.value ^ rotr64(word, 7).value ^ rotr64(word, 41).value)


def p_l(state: AsconState) -> AsconState:
    """Linear diffusion layer."""
    return AsconState(sigma0(state.x0), sigma1(state.x1), sigma2(state.x2), sigma3(state.x3), sigma4(state.x4))


def emit_verilog_rotr64_function() -> str:
    return "\n".join(
        (
            "function [63:0] ascon_rotr64;",
            "  input [63:0] x;",
            "  input [5:0]  amount;",
            "  begin",
            "    ascon_rotr64 = (x >> amount) | (x << (6'd64 - amount));",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_pl_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_p_l;",
            "  input [319:0] state;",
            "  reg [63:0] x0;",
            "  reg [63:0] x1;",
            "  reg [63:0] x2;",
            "  reg [63:0] x3;",
            "  reg [63:0] x4;",
            "  begin",
            "    x0 = state[63:0];",
            "    x1 = state[127:64];",
            "    x2 = state[191:128];",
            "    x3 = state[255:192];",
            "    x4 = state[319:256];",
            "    x0 = x0 ^ ascon_rotr64(x0, 6'd19) ^ ascon_rotr64(x0, 6'd28);",
            "    x1 = x1 ^ ascon_rotr64(x1, 6'd61) ^ ascon_rotr64(x1, 6'd39);",
            "    x2 = x2 ^ ascon_rotr64(x2, 6'd1)  ^ ascon_rotr64(x2, 6'd6);",
            "    x3 = x3 ^ ascon_rotr64(x3, 6'd10) ^ ascon_rotr64(x3, 6'd17);",
            "    x4 = x4 ^ ascon_rotr64(x4, 6'd7)  ^ ascon_rotr64(x4, 6'd41);",
            "    ascon_p_l = {x4, x3, x2, x1, x0};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_pl_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon linear diffusion layer p_L.",
            emit_verilog_rotr64_function(),
            emit_verilog_pl_function(),
        )
    )
