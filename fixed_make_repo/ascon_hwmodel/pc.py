from typing import Final

from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64

ROUND_CONSTANTS: Final[tuple[U64, ...]] = (
    U64(0x0000_0000_0000_003C),
    U64(0x0000_0000_0000_002D),
    U64(0x0000_0000_0000_001E),
    U64(0x0000_0000_0000_000F),
    U64(0x0000_0000_0000_00F0),
    U64(0x0000_0000_0000_00E1),
    U64(0x0000_0000_0000_00D2),
    U64(0x0000_0000_0000_00C3),
    U64(0x0000_0000_0000_00B4),
    U64(0x0000_0000_0000_00A5),
    U64(0x0000_0000_0000_0096),
    U64(0x0000_0000_0000_0087),
    U64(0x0000_0000_0000_0078),
    U64(0x0000_0000_0000_0069),
    U64(0x0000_0000_0000_005A),
    U64(0x0000_0000_0000_004B),
)


def check_rounds(rounds: int) -> None:
    if not isinstance(rounds, int):
        raise TypeError("rounds must be int")
    if rounds < 1 or rounds > 16:
        raise ValueError("rounds must satisfy 1 <= rounds <= 16")


def round_constant_index(rounds: int, round_index: int) -> int:
    check_rounds(rounds)
    if round_index < 0 or round_index >= rounds:
        raise ValueError(f"round_index must satisfy 0 <= round_index < {rounds}")
    return 16 - rounds + round_index


def round_constant(rounds: int, round_index: int) -> U64:
    return ROUND_CONSTANTS[round_constant_index(rounds, round_index)]


def p_c(state: AsconState, rounds: int, round_index: int) -> AsconState:
    """Constant-addition layer: x2 <- x2 xor c_i."""
    c: U64 = round_constant(rounds, round_index)
    return state.with_word(2, U64(state.x2.value ^ c.value))


def p_c_const_index(state: AsconState, const_index: int) -> AsconState:
    """Constant-addition layer using an explicit const0..const15 index."""
    if const_index < 0 or const_index >= len(ROUND_CONSTANTS):
        raise ValueError("const_index must satisfy 0 <= const_index < 16")
    return state.with_word(2, U64(state.x2.value ^ ROUND_CONSTANTS[const_index].value))


def emit_verilog_round_constants() -> str:
    lines: list[str] = ["// Ascon round constants const0..const15"]
    for index, constant in enumerate(ROUND_CONSTANTS):
        lines.append(f"localparam [63:0] ASCON_CONST_{index:02d} = {constant.verilog_literal()};")
    return "\n".join(lines)


def emit_verilog_round_constant_function() -> str:
    lines: list[str] = [
        "function [63:0] ascon_round_constant;",
        "  input [3:0] const_index;",
        "  begin",
        "    case (const_index)",
    ]
    for index, constant in enumerate(ROUND_CONSTANTS):
        lines.append(f"      4'd{index}: ascon_round_constant = {constant.verilog_literal()};")
    lines.extend(
        (
            "      default: ascon_round_constant = 64'h0000_0000_0000_0000;",
            "    endcase",
            "  end",
            "endfunction",
        )
    )
    return "\n".join(lines)


def emit_verilog_pc_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_p_c;",
            "  input [319:0] state;",
            "  input [3:0]   const_index;",
            "  reg [63:0] x0;",
            "  reg [63:0] x1;",
            "  reg [63:0] x2;",
            "  reg [63:0] x3;",
            "  reg [63:0] x4;",
            "  begin",
            "    x0 = state[63:0];",
            "    x1 = state[127:64];",
            "    x2 = state[191:128] ^ ascon_round_constant(const_index);",
            "    x3 = state[255:192];",
            "    x4 = state[319:256];",
            "    ascon_p_c = {x4, x3, x2, x1, x0};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_pc_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon constant-addition layer p_C.",
            emit_verilog_round_constants(),
            emit_verilog_round_constant_function(),
            emit_verilog_pc_function(),
        )
    )
