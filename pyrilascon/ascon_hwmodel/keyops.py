from ascon_hwmodel.iv import ascon_iv
from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64
from ascon_hwmodel.variants import AsconVariant
from ascon_hwmodel.word import Key128, Nonce128, Tag128


def aead128_initial_state_before_permutation(key: Key128, nonce: Nonce128) -> AsconState:
    """Build the AEAD128 initial state S <- IV || K || N before Ascon-p[12]."""
    key_low, key_high = key.words()
    nonce_low, nonce_high = nonce.words()
    return AsconState(ascon_iv(AsconVariant.AEAD128), key_low, key_high, nonce_low, nonce_high)


def aead128_add_key_after_initial_permutation(state: AsconState, key: Key128) -> AsconState:
    """Apply S <- S xor (0^192 || K) after the initial Ascon-p[12]."""
    key_low, key_high = key.words()
    return AsconState(
        state.x0,
        state.x1,
        state.x2,
        U64(state.x3.value ^ key_low.value),
        U64(state.x4.value ^ key_high.value),
    )


def aead128_add_key_before_final_permutation(state: AsconState, key: Key128) -> AsconState:
    """Apply S <- S xor (0^128 || K || 0^64) before final Ascon-p[12]."""
    key_low, key_high = key.words()
    return AsconState(
        state.x0,
        state.x1,
        U64(state.x2.value ^ key_low.value),
        U64(state.x3.value ^ key_high.value),
        state.x4,
    )


def aead128_extract_tag_after_final_permutation(state: AsconState, key: Key128) -> Tag128:
    """Compute T <- S[192:319] xor K after final Ascon-p[12]."""
    key_low, key_high = key.words()
    return Tag128.from_words(
        U64(state.x3.value ^ key_low.value),
        U64(state.x4.value ^ key_high.value),
    )


def emit_verilog_aead128_initial_state_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead128_initial_state;",
            "  input [127:0] key;",
            "  input [127:0] nonce;",
            "  begin",
            "    ascon_aead128_initial_state = {nonce[127:64], nonce[63:0], key[127:64], key[63:0], ASCON_AEAD128_IV};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_aead128_add_key_after_init_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead128_add_key_after_init;",
            "  input [319:0] state;",
            "  input [127:0] key;",
            "  begin",
            "    // S <- S xor (0^192 || K)",
            "    ascon_aead128_add_key_after_init = state ^ {key[127:0], 192'b0};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_aead128_add_key_before_final_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead128_add_key_before_final;",
            "  input [319:0] state;",
            "  input [127:0] key;",
            "  begin",
            "    // S <- S xor (0^128 || K || 0^64)",
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


def emit_verilog_keyops_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon AEAD key helpers. Include inside a module or package scope.",
            emit_verilog_aead128_initial_state_function(),
            emit_verilog_aead128_add_key_after_init_function(),
            emit_verilog_aead128_add_key_before_final_function(),
            emit_verilog_aead128_extract_tag_function(),
        )
    )
