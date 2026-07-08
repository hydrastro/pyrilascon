from ascon_hwmodel.absorb import absorb_block64_into_x0, absorb_block128_into_x0_x1
from ascon_hwmodel.domain import AEAD_DOMAIN_SEPARATOR_X4_MASK, aead_domain_separate_after_ad
from ascon_hwmodel.iv import ascon_iv
from ascon_hwmodel.keyops import (
    aead128_add_key_after_initial_permutation,
    aead128_add_key_before_final_permutation,
    aead128_extract_tag_after_final_permutation,
    aead128_initial_state_before_permutation,
)
from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64, U128
from ascon_hwmodel.variants import AsconVariant
from ascon_hwmodel.views import ByteSequenceHex, UIntHex
from ascon_hwmodel.word import Block64, Block128, Key128, Nonce128, Tag128


def test_byte_sequence_hex_is_not_uint_hex() -> None:
    byte_hex = ByteSequenceHex("0001020304050607")
    block = Block64.from_bytes(byte_hex.to_bytes())
    assert block.to_u64() == U64(0x0706_0504_0302_0100)
    assert UIntHex("0001020304050607", 64).to_int() == 0x0001_0203_0405_0607


def test_block128_words_are_little_endian() -> None:
    block = Block128.from_bytes(bytes(range(16)))
    assert block.low == U64(0x0706_0504_0302_0100)
    assert block.high == U64(0x0F0E_0D0C_0B0A_0908)
    assert block.to_bytes() == bytes(range(16))
    assert Block128.from_words(block.low, block.high) == block


def test_absorb_64_and_128() -> None:
    state = AsconState.zero()
    block64 = Block64.from_int(0x1122_3344_5566_7788)
    assert absorb_block64_into_x0(state, block64) == AsconState(
        U64(0x1122_3344_5566_7788), U64(0), U64(0), U64(0), U64(0)
    )

    block128 = Block128.from_words(U64(0x0102_0304_0506_0708), U64(0x1112_1314_1516_1718))
    assert absorb_block128_into_x0_x1(state, block128) == AsconState(
        U64(0x0102_0304_0506_0708), U64(0x1112_1314_1516_1718), U64(0), U64(0), U64(0)
    )


def test_aead_domain_separator_toggles_state_bit_319() -> None:
    separated = aead_domain_separate_after_ad(AsconState.zero())
    assert separated.x0 == U64(0)
    assert separated.x1 == U64(0)
    assert separated.x2 == U64(0)
    assert separated.x3 == U64(0)
    assert separated.x4 == AEAD_DOMAIN_SEPARATOR_X4_MASK
    assert separated.to_int() == 1 << 319


def test_aead128_key_and_nonce_layout() -> None:
    key = Key128.from_bytes(bytes(range(16)))
    nonce = Nonce128.from_bytes(bytes(range(16, 32)))
    state = aead128_initial_state_before_permutation(key, nonce)
    assert state == AsconState(
        ascon_iv(AsconVariant.AEAD128),
        U64(0x0706_0504_0302_0100),
        U64(0x0F0E_0D0C_0B0A_0908),
        U64(0x1716_1514_1312_1110),
        U64(0x1F1E_1D1C_1B1A_1918),
    )


def test_aead128_key_injection_and_tag_extract() -> None:
    key = Key128.from_words(U64(0x1111_1111_1111_1111), U64(0x2222_2222_2222_2222))
    state = AsconState(U64(0), U64(1), U64(2), U64(3), U64(4))

    after_init = aead128_add_key_after_initial_permutation(state, key)
    assert after_init == AsconState(
        U64(0),
        U64(1),
        U64(2),
        U64(0x1111_1111_1111_1112),
        U64(0x2222_2222_2222_2226),
    )

    before_final = aead128_add_key_before_final_permutation(state, key)
    assert before_final == AsconState(
        U64(0),
        U64(1),
        U64(0x1111_1111_1111_1113),
        U64(0x2222_2222_2222_2221),
        U64(4),
    )

    tag = aead128_extract_tag_after_final_permutation(state, key)
    assert isinstance(tag, Tag128)
    assert tag.value == U128(0x2222_2222_2222_2226_1111_1111_1111_1112)
