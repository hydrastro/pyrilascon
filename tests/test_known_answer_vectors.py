from dataclasses import dataclass

from ascon_hwmodel.aead import ascon_aead128_decrypt, ascon_aead128_encrypt
from ascon_hwmodel.hash_xof import ascon_cxof128, ascon_hash256, ascon_xof128


@dataclass(frozen=True, slots=True)
class AeadKat:
    count: int
    key_hex: str
    nonce_hex: str
    plaintext_hex: str
    associated_data_hex: str
    ciphertext_tag_hex: str


NIST_AEAD128_KEY = "000102030405060708090A0B0C0D0E0F"
NIST_AEAD128_NONCE = "101112131415161718191A1B1C1D1E1F"


# Subset of official Ascon-AEAD128 LWC known-answer vectors.
# Source: ascon/ascon-c crypto_aead/asconaead128/LWC_AEAD_KAT_128_128.txt
NIST_AEAD128_KATS = (
    AeadKat(
        count=1,
        key_hex=NIST_AEAD128_KEY,
        nonce_hex=NIST_AEAD128_NONCE,
        plaintext_hex="",
        associated_data_hex="",
        ciphertext_tag_hex="4F9C278211BEC9316BF68F46EE8B2EC6",
    ),
    AeadKat(
        count=2,
        key_hex=NIST_AEAD128_KEY,
        nonce_hex=NIST_AEAD128_NONCE,
        plaintext_hex="",
        associated_data_hex="30",
        ciphertext_tag_hex="CCCB674FE18A09A285D6AB11B35675C0",
    ),
    AeadKat(
        count=3,
        key_hex=NIST_AEAD128_KEY,
        nonce_hex=NIST_AEAD128_NONCE,
        plaintext_hex="",
        associated_data_hex="3031",
        ciphertext_tag_hex="F65B191550C4DF9CFDD4460EBBCCA782",
    ),
    AeadKat(
        count=4,
        key_hex=NIST_AEAD128_KEY,
        nonce_hex=NIST_AEAD128_NONCE,
        plaintext_hex="",
        associated_data_hex="303132",
        ciphertext_tag_hex="D127CF7D2CD4DA8930616C70B3619F42",
    ),
    AeadKat(
        count=36,
        key_hex=NIST_AEAD128_KEY,
        nonce_hex=NIST_AEAD128_NONCE,
        plaintext_hex="20",
        associated_data_hex="30",
        ciphertext_tag_hex="962B8016836C75A7D86866588CA245D886",
    ),
    AeadKat(
        count=67,
        key_hex=NIST_AEAD128_KEY,
        nonce_hex=NIST_AEAD128_NONCE,
        plaintext_hex="2021",
        associated_data_hex="",
        ciphertext_tag_hex="E8C35A12D2A396E76224F6EE5418F6465197",
    ),
    AeadKat(
        count=68,
        key_hex=NIST_AEAD128_KEY,
        nonce_hex=NIST_AEAD128_NONCE,
        plaintext_hex="2021",
        associated_data_hex="30",
        ciphertext_tag_hex="9610D39E0CD43E61F7D01A1B636FD60FB19F",
    ),
)


def test_nist_aead128_known_answer_vectors_encrypt_decrypt():
    for kat in NIST_AEAD128_KATS:
        key = bytes.fromhex(kat.key_hex)
        nonce = bytes.fromhex(kat.nonce_hex)
        plaintext = bytes.fromhex(kat.plaintext_hex)
        associated_data = bytes.fromhex(kat.associated_data_hex)
        expected = bytes.fromhex(kat.ciphertext_tag_hex)
        expected_ciphertext = expected[: len(plaintext)]
        expected_tag = expected[len(plaintext) :]

        encrypted = ascon_aead128_encrypt(key, nonce, associated_data, plaintext)
        assert encrypted.ciphertext == expected_ciphertext, f"Count {kat.count}: ciphertext mismatch"
        assert encrypted.tag == expected_tag, f"Count {kat.count}: tag mismatch"

        decrypted = ascon_aead128_decrypt(key, nonce, associated_data, encrypted.ciphertext, encrypted.tag)
        assert decrypted.valid, f"Count {kat.count}: valid tag rejected"
        assert decrypted.plaintext == plaintext, f"Count {kat.count}: plaintext mismatch"

        bad_tag = encrypted.tag[:-1] + bytes([encrypted.tag[-1] ^ 0x01])
        rejected = ascon_aead128_decrypt(key, nonce, associated_data, encrypted.ciphertext, bad_tag)
        assert not rejected.valid, f"Count {kat.count}: invalid tag accepted"


def test_nist_hash256_empty_message_known_answer():
    assert (
        ascon_hash256(b"").hex().upper()
        == "0B3BE5850F2F6B98CAF29F8FDEA89B64A1FA70AA249B8F839BD53BAA304D92B2"
    )


def test_nist_xof128_empty_message_512_bit_known_answer():
    assert (
        ascon_xof128(b"", 64).hex().upper()
        == "473D5E6164F58B39DFD84AACDB8AE42EC2D91FED33388EE0D960D9B3993295C6"
        "AD77855A5D3B13FE6AD9E6098988373AF7D0956D05A8F1665D2C67D1A3AD10FF"
    )


def test_nist_cxof128_empty_customization_single_zero_message_known_answer():
    assert (
        ascon_cxof128(bytes.fromhex("00"), 64, b"").hex().upper()
        == "7F0C0DDD4BC9603DEED19510CDB954D65CF254F59234BFBF5A730D03D2712DAA"
        "B9161C6553F65FA72A25B3174AC13A33218C393577A85B6D6F4319D1EF8A7541"
    )
