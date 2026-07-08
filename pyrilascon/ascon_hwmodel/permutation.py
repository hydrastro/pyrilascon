"""Compatibility facade for the Ascon permutation model.

The implementation is intentionally split by layer and permutation size:
- pc.py: constant-addition layer p_C and round constants
- ps.py: substitution layer p_S, including LUT reference and bitsliced form
- pl.py: linear diffusion layer p_L
- round.py: round composition and trace support
- p6.py, p8.py, p12.py: the three standardized permutation wrappers
"""

from ascon_hwmodel.p6 import ascon_p6, emit_verilog_p6_function, emit_verilog_p6_include, emit_verilog_p6_module
from ascon_hwmodel.p8 import ascon_p8, emit_verilog_p8_function, emit_verilog_p8_include, emit_verilog_p8_module
from ascon_hwmodel.p12 import ascon_p12, emit_verilog_p12_function, emit_verilog_p12_include, emit_verilog_p12_module
from ascon_hwmodel.pc import (
    ROUND_CONSTANTS,
    check_rounds,
    emit_verilog_pc_function,
    emit_verilog_pc_include,
    emit_verilog_round_constant_function,
    emit_verilog_round_constants,
    p_c,
    p_c_const_index,
    round_constant,
    round_constant_index,
)
from ascon_hwmodel.pl import (
    MASK64,
    emit_verilog_pl_function,
    emit_verilog_pl_include,
    emit_verilog_rotr64_function,
    p_l,
    rotr64,
    sigma0,
    sigma1,
    sigma2,
    sigma3,
    sigma4,
)
from ascon_hwmodel.ps import (
    SBOX,
    emit_verilog_ps_bitsliced_function,
    emit_verilog_ps_function,
    emit_verilog_ps_include,
    emit_verilog_ps_lut_function,
    emit_verilog_sbox5_lut_function,
    p_s,
    p_s_bitsliced,
    p_s_lut,
    sbox5_bits,
    sbox5_value,
)
from ascon_hwmodel.round import (
    PermutationTraceEntry,
    ascon_permutation,
    ascon_permutation_trace,
    ascon_round,
    emit_verilog_round_function,
    emit_verilog_round_include,
)


def emit_verilog_permutation_functions() -> str:
    return "\n\n".join(
        (
            emit_verilog_round_function(),
            emit_verilog_p6_function(),
            emit_verilog_p8_function(),
            emit_verilog_p12_function(),
        )
    )


def emit_verilog_permutation_comb_module() -> str:
    """Emit a standalone combinational Verilog module for p6/p8/p12 selection."""
    return "\n".join(
        (
            "`include \"ascon_model.vh\"",
            "",
            "module ascon_permutation_comb(",
            "  input  wire [319:0] state_i,",
            "  input  wire [1:0]   rounds_i, // 0:p6, 1:p8, 2:p12",
            "  output reg  [319:0] state_o",
            ");",
            "  always @* begin",
            "    case (rounds_i)",
            "      2'd0: state_o = ascon_p6(state_i);",
            "      2'd1: state_o = ascon_p8(state_i);",
            "      2'd2: state_o = ascon_p12(state_i);",
            "      default: state_o = 320'b0;",
            "    endcase",
            "  end",
            "endmodule",
        )
    )


def emit_verilog_permutation_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon permutation helpers. Include inside a module or package scope.",
            emit_verilog_pc_include(),
            emit_verilog_ps_include(),
            emit_verilog_pl_include(),
            emit_verilog_round_include(),
            emit_verilog_p6_include(),
            emit_verilog_p8_include(),
            emit_verilog_p12_include(),
        )
    )
