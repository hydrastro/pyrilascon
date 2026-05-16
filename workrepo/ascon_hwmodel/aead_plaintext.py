from dataclasses import dataclass

from ascon_hwmodel.aead_config import AEADConfig
from ascon_hwmodel.byteops import parse_bytes
from ascon_hwmodel.rate import rate_bytes_from_state, replace_rate_bytes, xor_rate_bytes
from ascon_hwmodel.round import ascon_permutation
from ascon_hwmodel.state import AsconState


@dataclass(frozen=True, slots=True)
class AEADPlaintextResult:
    state: AsconState
    ciphertext: bytes


def aead_encrypt_plaintext(state: AsconState, plaintext: bytes, config: AEADConfig) -> AEADPlaintextResult:
    parsed = parse_bytes(plaintext, config.rate_bytes)
    output = bytearray()
    for block in parsed.full_blocks:
        state = xor_rate_bytes(state, block, config.rate_bytes)
        output.extend(rate_bytes_from_state(state, config.rate_bytes))
        state = ascon_permutation(state, config.intermediate_rounds)
    final_padded: bytes = parsed.padded_final_block()
    state = xor_rate_bytes(state, final_padded, config.rate_bytes)
    output.extend(rate_bytes_from_state(state, config.rate_bytes)[: len(parsed.final_block)])
    return AEADPlaintextResult(state, bytes(output))


def emit_verilog_aead_plaintext_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon AEAD plaintext-processing helper functions.",
            emit_verilog_aead_encrypt_full_block_function(),
            emit_verilog_aead_encrypt_final_state_function(),
        )
    )


def emit_verilog_aead_encrypt_full_block_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead_encrypt_full_block_state;",
            "  input [319:0] state;",
            "  input [127:0] plaintext_block;",
            "  input         rate128;",
            "  input [3:0]   rounds;",
            "  begin",
            "    ascon_aead_encrypt_full_block_state = ascon_rounds(ascon_rate_xor(state, plaintext_block, rate128), rounds);",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_aead_encrypt_final_state_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead_encrypt_final_state;",
            "  input [319:0] state;",
            "  input [127:0] padded_final_plaintext;",
            "  input         rate128;",
            "  begin",
            "    ascon_aead_encrypt_final_state = ascon_rate_xor(state, padded_final_plaintext, rate128);",
            "  end",
            "endfunction",
        )
    )
