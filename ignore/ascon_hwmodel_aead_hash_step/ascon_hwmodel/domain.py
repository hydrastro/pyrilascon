from typing import Final

from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64

AEAD_DOMAIN_SEPARATOR_BIT_INDEX: Final[int] = 319
AEAD_DOMAIN_SEPARATOR_X4_MASK: Final[U64] = U64(1 << 63)


def aead_domain_separate_after_ad(state: AsconState) -> AsconState:
    """Apply S <- S xor (0^319 || 1) after associated-data processing.

    In the little-endian state representation, this is bit S[319], which is the
    most-significant bit of x4, not bit 0 of x0.
    """
    return state.with_word(4, U64(state.x4.value ^ AEAD_DOMAIN_SEPARATOR_X4_MASK.value))


def verilog_aead_domain_separator_mask() -> str:
    return "{1'b1, 319'b0}"


def emit_verilog_domain_separator_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead_domain_separator;",
            "  input [319:0] state;",
            "  begin",
            "    // S <- S xor (0^319 || 1): toggle logical bit S[319] = state[319].",
            f"    ascon_aead_domain_separator = state ^ {verilog_aead_domain_separator_mask()};",
            "  end",
            "endfunction",
        )
    )
