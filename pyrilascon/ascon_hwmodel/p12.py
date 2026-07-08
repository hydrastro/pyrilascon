from ascon_hwmodel.round import ascon_permutation
from ascon_hwmodel.state import AsconState


def ascon_p12(state: AsconState) -> AsconState:
    return ascon_permutation(state, 12)


def emit_verilog_p12_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_p12;",
            "  input [319:0] state;",
            "  reg [319:0] s;",
            "  integer i;",
            "  begin",
            "    s = state;",
            "    for (i = 4; i < 16; i = i + 1) begin",
            "      s = ascon_round_const_index(s, i[3:0]);",
            "    end",
            "    ascon_p12 = s;",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_p12_include() -> str:
    return "\n\n".join(("// Generated Ascon-p[12] function.", emit_verilog_p12_function()))


def emit_verilog_p12_module() -> str:
    return "\n".join(
        (
            "`include \"ascon_model.vh\"",
            "",
            "module ascon_p12_comb(",
            "  input  wire [319:0] state_i,",
            "  output wire [319:0] state_o",
            ");",
            "  assign state_o = ascon_p12(state_i);",
            "endmodule",
        )
    )
