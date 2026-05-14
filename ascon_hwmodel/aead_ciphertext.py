from dataclasses import dataclass

from ascon_hwmodel.aead_config import AEADConfig
from ascon_hwmodel.byteops import parse_bytes
from ascon_hwmodel.rate import rate_bytes_from_state, replace_rate_bytes
from ascon_hwmodel.round import ascon_permutation
from ascon_hwmodel.state import AsconState


@dataclass(frozen=True, slots=True)
class AEADCiphertextResult:
    state: AsconState
    plaintext: bytes


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        raise ValueError("byte strings must have equal length")
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


def aead_decrypt_ciphertext(state: AsconState, ciphertext: bytes, config: AEADConfig) -> AEADCiphertextResult:
    parsed = parse_bytes(ciphertext, config.rate_bytes)
    output = bytearray()
    for block in parsed.full_blocks:
        rate_before: bytes = rate_bytes_from_state(state, config.rate_bytes)
        output.extend(_xor_bytes(rate_before, block))
        state = replace_rate_bytes(state, block, config.rate_bytes)
        state = ascon_permutation(state, config.intermediate_rounds)

    final_len: int = len(parsed.final_block)
    rate_final: bytearray = bytearray(rate_bytes_from_state(state, config.rate_bytes))
    output.extend(_xor_bytes(bytes(rate_final[:final_len]), parsed.final_block))
    rate_final[:final_len] = parsed.final_block
    rate_final[final_len] ^= 0x01
    state = replace_rate_bytes(state, bytes(rate_final), config.rate_bytes)
    return AEADCiphertextResult(state, bytes(output))


def emit_verilog_aead_ciphertext_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon AEAD ciphertext-processing helper functions.",
            emit_verilog_aead_decrypt_full_block_state_function(),
            emit_verilog_aead_decrypt_full_block_plaintext_function(),
        )
    )


def emit_verilog_aead_decrypt_full_block_plaintext_function() -> str:
    return "\n".join(
        (
            "function [127:0] ascon_aead_decrypt_full_block_plaintext;",
            "  input [319:0] state;",
            "  input [127:0] ciphertext_block;",
            "  input         rate128;",
            "  begin",
            "    ascon_aead_decrypt_full_block_plaintext = ascon_rate_select(state, rate128) ^ ciphertext_block;",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_aead_decrypt_full_block_state_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead_decrypt_full_block_state;",
            "  input [319:0] state;",
            "  input [127:0] ciphertext_block;",
            "  input         rate128;",
            "  input [3:0]   rounds;",
            "  begin",
            "    ascon_aead_decrypt_full_block_state = ascon_rounds(ascon_rate_replace(state, ciphertext_block, rate128), rounds);",
            "  end",
            "endfunction",
        )
    )
