from ascon_hwmodel import (
    AEADVariant,
    aead_decrypt,
    aead_encrypt,
    aead_process_associated_data,
    aead_initialize,
    get_aead_config,
)
from ascon_hwmodel.aead_ciphertext import aead_decrypt_ciphertext
from ascon_hwmodel.aead_plaintext import aead_encrypt_plaintext


def test_nist_aead128_empty_roundtrip():
    key = bytes(range(16))
    nonce = bytes(range(16, 32))
    enc = aead_encrypt(key, nonce, b"", b"", AEADVariant.NIST_AEAD128)
    dec = aead_decrypt(key, nonce, b"", enc.ciphertext, enc.tag, AEADVariant.NIST_AEAD128)
    assert enc.ciphertext == b""
    assert dec.valid
    assert dec.plaintext == b""


def test_nist_aead128_various_lengths_roundtrip():
    key = bytes(range(16))
    nonce = bytes(reversed(range(16)))
    associated_data = b"header-data" * 3
    for length in list(range(0, 40)) + [63, 64, 65, 127, 128, 129]:
        plaintext = bytes((i * 7 + 3) & 0xFF for i in range(length))
        enc = aead_encrypt(key, nonce, associated_data, plaintext)
        dec = aead_decrypt(key, nonce, associated_data, enc.ciphertext, enc.tag)
        assert dec.valid
        assert dec.plaintext == plaintext
        assert len(enc.ciphertext) == len(plaintext)


def test_tampered_tag_invalid():
    key = bytes(range(16))
    nonce = b"N" * 16
    enc = aead_encrypt(key, nonce, b"ad", b"message")
    bad_tag = enc.tag[:-1] + bytes([enc.tag[-1] ^ 1])
    dec = aead_decrypt(key, nonce, b"ad", enc.ciphertext, bad_tag)
    assert not dec.valid


def test_shared_initialization_and_ad_for_encrypt_and_decrypt():
    key = bytes(range(16))
    nonce = bytes(range(16, 32))
    ad = b"associated data"
    cfg = get_aead_config(AEADVariant.NIST_AEAD128)
    s0 = aead_initialize(key, nonce, cfg)
    s1 = aead_process_associated_data(s0, ad, cfg)
    enc_pt = aead_encrypt_plaintext(s1, b"plaintext", cfg)
    dec_ct = aead_decrypt_ciphertext(s1, enc_pt.ciphertext, cfg)
    assert dec_ct.plaintext == b"plaintext"
