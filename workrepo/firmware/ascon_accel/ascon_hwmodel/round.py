from dataclasses import dataclass

from ascon_hwmodel.pc import ROUND_CONSTANTS, check_rounds, p_c, round_constant_index
from ascon_hwmodel.pl import p_l
from ascon_hwmodel.ps import p_s
from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64


@dataclass(frozen=True, slots=True)
class PermutationTraceEntry:
    round_index: int
    constant_index: int
    constant: U64
    state_after_pc: AsconState
    state_after_ps: AsconState
    state_after_pl: AsconState


def ascon_round(state: AsconState, rounds: int, round_index: int) -> AsconState:
    return p_l(p_s(p_c(state, rounds, round_index)))


def ascon_permutation(state: AsconState, rounds: int) -> AsconState:
    check_rounds(rounds)
    current: AsconState = state
    for round_index in range(rounds):
        current = ascon_round(current, rounds, round_index)
    return current


def ascon_permutation_trace(state: AsconState, rounds: int) -> tuple[PermutationTraceEntry, ...]:
    check_rounds(rounds)
    entries: list[PermutationTraceEntry] = []
    current: AsconState = state
    for round_index in range(rounds):
        const_index: int = round_constant_index(rounds, round_index)
        after_pc: AsconState = p_c(current, rounds, round_index)
        after_ps: AsconState = p_s(after_pc)
        after_pl: AsconState = p_l(after_ps)
        entries.append(PermutationTraceEntry(round_index, const_index, ROUND_CONSTANTS[const_index], after_pc, after_ps, after_pl))
        current = after_pl
    return tuple(entries)


def emit_verilog_round_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_round_const_index;",
            "  input [319:0] state;",
            "  input [3:0]   const_index;",
            "  begin",
            "    ascon_round_const_index = ascon_p_l(ascon_p_s(ascon_p_c(state, const_index)));",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_rounds_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_rounds;",
            "  input [319:0] state;",
            "  input [3:0]   rounds;",
            "  begin",
            "    case (rounds)",
            "      4'd6:  ascon_rounds = ascon_p6(state);",
            "      4'd8:  ascon_rounds = ascon_p8(state);",
            "      4'd12: ascon_rounds = ascon_p12(state);",
            "      default: ascon_rounds = 320'b0;",
            "    endcase",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_round_include() -> str:
    return "\n\n".join(("// Generated Ascon round composition.", emit_verilog_round_function()))
