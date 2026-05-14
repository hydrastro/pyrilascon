from dataclasses import dataclass

from ascon_hwmodel.aead_ad import aead_process_associated_data
from ascon_hwmodel.aead_config import AEADConfig, AEADVariant, get_aead_config
from ascon_hwmodel.aead_final import aead_finalize
from ascon_hwmodel.aead_init import aead_initialize
from ascon_hwmodel.aead_plaintext import aead_encrypt_plaintext
from ascon_hwmodel.state import AsconState


@dataclass(frozen=True, slots=True)
class AEADEncryptionResult:
    ciphertext: bytes
    tag: bytes
    state_after_initialization: AsconState
    state_after_associated_data: AsconState
    state_after_plaintext: AsconState


def aead_encrypt(
    key: bytes,
    nonce: bytes,
    associated_data: bytes,
    plaintext: bytes,
    variant: AEADVariant = AEADVariant.NIST_AEAD128,
) -> AEADEncryptionResult:
    config: AEADConfig = get_aead_config(variant)
    state: AsconState = aead_initialize(key, nonce, config)
    state_after_init: AsconState = state
    state = aead_process_associated_data(state, associated_data, config)
    state_after_ad: AsconState = state
    pt_result = aead_encrypt_plaintext(state, plaintext, config)
    tag: bytes = aead_finalize(pt_result.state, key, config)
    return AEADEncryptionResult(pt_result.ciphertext, tag, state_after_init, state_after_ad, pt_result.state)
