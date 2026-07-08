from ascon_hwmodel.aead_config import AEADConfig, AEADVariant, AEAD_CONFIGS, get_aead_config
from ascon_hwmodel.aead_decrypt import AEADDecryptionResult, aead_decrypt
from ascon_hwmodel.aead_encrypt import AEADEncryptionResult, aead_encrypt


def ascon_aead128_encrypt(key: bytes, nonce: bytes, associated_data: bytes, plaintext: bytes) -> AEADEncryptionResult:
    return aead_encrypt(key, nonce, associated_data, plaintext, AEADVariant.NIST_AEAD128)


def ascon_aead128_decrypt(key: bytes, nonce: bytes, associated_data: bytes, ciphertext: bytes, tag: bytes) -> AEADDecryptionResult:
    return aead_decrypt(key, nonce, associated_data, ciphertext, tag, AEADVariant.NIST_AEAD128)


def emit_verilog_aead_include() -> str:
    from ascon_hwmodel.aead_ad import emit_verilog_aead_ad_include
    from ascon_hwmodel.aead_ciphertext import emit_verilog_aead_ciphertext_include
    from ascon_hwmodel.aead_config import emit_verilog_aead_config_include
    from ascon_hwmodel.aead_final import emit_verilog_aead_final_include
    from ascon_hwmodel.aead_init import emit_verilog_aead_init_include
    from ascon_hwmodel.aead_plaintext import emit_verilog_aead_plaintext_include
    from ascon_hwmodel.round import emit_verilog_rounds_function

    return "\n\n".join(
        (
            emit_verilog_aead_config_include(),
            emit_verilog_rounds_function(),
            emit_verilog_aead_init_include(),
            emit_verilog_aead_ad_include(),
            emit_verilog_aead_plaintext_include(),
            emit_verilog_aead_ciphertext_include(),
            emit_verilog_aead_final_include(),
        )
    )
