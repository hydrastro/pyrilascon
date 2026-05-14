from ascon_hwmodel.aead_config import AEADConfig
from ascon_hwmodel.p12 import ascon_p12
from ascon_hwmodel.state import AsconState
from ascon_hwmodel.word import Tag128


def aead_add_key_before_final_permutation(state: AsconState, key: bytes, config: AEADConfig) -> AsconState:
    config.check_key(key)
    image: bytearray = bytearray(state.to_bytes())
    # For NIST AEAD128: S ^= 0^128 || K || 0^64, i.e. state bytes [16:32] ^= key.
    # Generalized as: place key immediately before the final 64-bit state word.
    start: int = 40 - 8 - config.key_bytes
    if start < 0:
        raise ValueError(f"cannot place {config.key_bytes}-byte key before final 64-bit word")
    for index, value in enumerate(key):
        image[start + index] ^= value
    return AsconState.from_bytes(bytes(image))


def aead_extract_tag_after_final_permutation(state: AsconState, key: bytes, config: AEADConfig) -> bytes:
    config.check_key(key)
    # For NIST AEAD128: T = S[192:319] ^ K, i.e. state bytes [24:40] ^ key.
    image: bytes = state.to_bytes()
    start: int = 40 - config.tag_bytes
    tag_state: bytes = image[start : start + config.tag_bytes]
    key_tail: bytes = key[-config.tag_bytes :]
    return bytes(a ^ b for a, b in zip(tag_state, key_tail, strict=True))


def aead_finalize(state: AsconState, key: bytes, config: AEADConfig) -> bytes:
    state = aead_add_key_before_final_permutation(state, key, config)
    state = ascon_p12(state)
    return aead_extract_tag_after_final_permutation(state, key, config)


def emit_verilog_aead_final_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon AEAD finalization helpers.",
            emit_verilog_aead128_add_key_before_final_function(),
            emit_verilog_aead128_extract_tag_function(),
        )
    )


def emit_verilog_aead128_add_key_before_final_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead128_add_key_before_final;",
            "  input [319:0] state;",
            "  input [127:0] key;",
            "  begin",
            "    // S <- S xor (0^128 || K || 0^64), little-endian state vector indexing.",
            "    ascon_aead128_add_key_before_final = state ^ {64'b0, key[127:0], 128'b0};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_aead128_extract_tag_function() -> str:
    return "\n".join(
        (
            "function [127:0] ascon_aead128_extract_tag;",
            "  input [319:0] state;",
            "  input [127:0] key;",
            "  begin",
            "    ascon_aead128_extract_tag = state[319:192] ^ key;",
            "  end",
            "endfunction",
        )
    )
