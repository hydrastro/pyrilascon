from dataclasses import dataclass

from ascon_hwmodel.aead_ad import aead_process_associated_data
from ascon_hwmodel.aead_ciphertext import aead_decrypt_ciphertext
from ascon_hwmodel.aead_config import AEADConfig, AEADVariant, get_aead_config
from ascon_hwmodel.aead_final import aead_finalize
from ascon_hwmodel.aead_init import aead_initialize
from ascon_hwmodel.state import AsconState


@dataclass(frozen=True, slots=True)
class AEADDecryptionResult:
    plaintext: bytes
    valid: bool
    computed_tag: bytes
    state_after_initialization: AsconState
    state_after_associated_data: AsconState
    state_after_ciphertext: AsconState


def aead_decrypt(
    key: bytes,
    nonce: bytes,
    associated_data: bytes,
    ciphertext: bytes,
    tag: bytes,
    variant: AEADVariant = AEADVariant.NIST_AEAD128,
) -> AEADDecryptionResult:
    config: AEADConfig = get_aead_config(variant)
    config.check_tag(tag)
    state: AsconState = aead_initialize(key, nonce, config)
    state_after_init: AsconState = state
    state = aead_process_associated_data(state, associated_data, config)
    state_after_ad: AsconState = state
    ct_result = aead_decrypt_ciphertext(state, ciphertext, config)
    computed_tag: bytes = aead_finalize(ct_result.state, key, config)
    return AEADDecryptionResult(
        plaintext=ct_result.plaintext,
        valid=(computed_tag == tag),
        computed_tag=computed_tag,
        state_after_initialization=state_after_init,
        state_after_associated_data=state_after_ad,
        state_after_ciphertext=ct_result.state,
    )
