from ascon_hwmodel.aead_config import AEADConfig
from ascon_hwmodel.byteops import pad_bytes, parse_bytes
from ascon_hwmodel.domain import aead_domain_separate_after_ad
from ascon_hwmodel.rate import xor_rate_bytes
from ascon_hwmodel.round import ascon_permutation
from ascon_hwmodel.state import AsconState


def aead_process_associated_data(state: AsconState, associated_data: bytes, config: AEADConfig) -> AsconState:
    if len(associated_data) > 0:
        parsed = parse_bytes(associated_data, config.rate_bytes)
        for block in parsed.full_blocks:
            state = xor_rate_bytes(state, block, config.rate_bytes)
            state = ascon_permutation(state, config.intermediate_rounds)
        state = xor_rate_bytes(state, parsed.padded_final_block(), config.rate_bytes)
        state = ascon_permutation(state, config.intermediate_rounds)
    return aead_domain_separate_after_ad(state)


def emit_verilog_aead_ad_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon AEAD associated-data helper functions.",
            emit_verilog_aead_absorb_ad_block_function(),
        )
    )


def emit_verilog_aead_absorb_ad_block_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead_absorb_ad_block;",
            "  input [319:0] state;",
            "  input [127:0] block;",
            "  input         rate128;",
            "  input [3:0]   rounds;",
            "  begin",
            "    ascon_aead_absorb_ad_block = ascon_rounds(ascon_rate_xor(state, block, rate128), rounds);",
            "  end",
            "endfunction",
        )
    )
