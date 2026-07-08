from ascon_hwmodel.round import ascon_permutation
from ascon_hwmodel.state import AsconState


def ascon_p8(state: AsconState) -> AsconState:
    return ascon_permutation(state, 8)


def emit_verilog_p8_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_p8;",
            "  input [319:0] state;",
            "  reg [319:0] s;",
            "  integer i;",
            "  begin",
            "    s = state;",
            "    for (i = 8; i < 16; i = i + 1) begin",
            "      s = ascon_round_const_index(s, i[3:0]);",
            "    end",
            "    ascon_p8 = s;",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_p8_include() -> str:
    return "\n\n".join(("// Generated Ascon-p[8] function.", emit_verilog_p8_function()))


def emit_verilog_p8_module() -> str:
    return "\n".join(
        (
            "`include \"ascon_model.vh\"",
            "",
            "module ascon_p8_comb(",
            "  input  wire [319:0] state_i,",
            "  output wire [319:0] state_o",
            ");",
            "  assign state_o = ascon_p8(state_i);",
            "endmodule",
        )
    )
