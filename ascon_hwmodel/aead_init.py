from ascon_hwmodel.aead_config import AEADConfig, AEADVariant, get_aead_config
from ascon_hwmodel.p12 import ascon_p12
from ascon_hwmodel.state import AsconState


def aead_initial_state_before_permutation(key: bytes, nonce: bytes, config: AEADConfig) -> AsconState:
    config.check_key(key)
    config.check_nonce(nonce)
    image: bytes = config.iv_bytes + key + nonce
    if len(image) != 40:
        raise ValueError(
            f"{config.variant.value} initialization image must be 40 bytes, got {len(image)}; "
            "check IV/key/nonce sizes"
        )
    return AsconState.from_bytes(image)


def aead_initialize(key: bytes, nonce: bytes, config: AEADConfig | None = None) -> AsconState:
    cfg: AEADConfig = config if config is not None else get_aead_config(AEADVariant.NIST_AEAD128)
    state: AsconState = aead_initial_state_before_permutation(key, nonce, cfg)
    state = ascon_p12(state)
    return aead_add_key_after_initial_permutation(state, key, cfg)


def aead_add_key_after_initial_permutation(state: AsconState, key: bytes, config: AEADConfig) -> AsconState:
    config.check_key(key)
    # Key occupies the last key_bytes of the 320-bit initialization image, excluding nonce.
    # For NIST AEAD128 this is S ^= 0^192 || K, i.e. state bytes [24:40] ^= key.
    image: bytearray = bytearray(state.to_bytes())
    start: int = 40 - config.key_bytes
    for index, value in enumerate(key):
        image[start + index] ^= value
    return AsconState.from_bytes(bytes(image))


def emit_verilog_aead_init_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon AEAD initialization helpers.",
            emit_verilog_aead128_initial_state_function(),
            emit_verilog_aead128_init_finish_function(),
        )
    )


def emit_verilog_aead128_initial_state_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead128_initial_state;",
            "  input [127:0] key;",
            "  input [127:0] nonce;",
            "  begin",
            "    // state[63:0]=IV, state[191:64]=key, state[319:192]=nonce",
            "    ascon_aead128_initial_state = {nonce[127:0], key[127:0], ASCON_AEAD128_IV};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_aead128_init_finish_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_aead128_init_finish;",
            "  input [319:0] state_after_p12;",
            "  input [127:0] key;",
            "  begin",
            "    // S <- S xor (0^192 || K), with little-endian state vector indexing.",
            "    ascon_aead128_init_finish = state_after_p12 ^ {key[127:0], 192'b0};",
            "  end",
            "endfunction",
        )
    )
