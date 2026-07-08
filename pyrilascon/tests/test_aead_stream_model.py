import pytest

from ascon_hwmodel.aead import ascon_aead128_decrypt, ascon_aead128_encrypt
from ascon_hwmodel.aead_stream import (
    AeadStreamKind,
    AxisStreamBeat,
    axis_aead128_decrypt,
    axis_aead128_encrypt,
    keep_mask,
    pack_axis_beats,
    unpack_axis_beats,
    valid_byte_count_from_keep,
)


def patterned(length: int, seed: int) -> bytes:
    return bytes(((index * 13) + seed) & 0xFF for index in range(length))


def test_keep_masks_are_contiguous_low_byte_masks() -> None:
    assert keep_mask(0, 16) == 0x0000
    assert keep_mask(1, 16) == 0x0001
    assert keep_mask(8, 16) == 0x00FF
    assert keep_mask(16, 16) == 0xFFFF
    assert valid_byte_count_from_keep(0x00FF, 16) == 8
    with pytest.raises(ValueError, match="not contiguous"):
        valid_byte_count_from_keep(0b0101, 8)


def test_pack_and_unpack_axis_beats_roundtrip_partial_final_beat() -> None:
    data = patterned(41, 0x21)
    beats = pack_axis_beats(data, AeadStreamKind.TEXT, bus_bytes=16)
    assert len(beats) == 3
    assert beats[0].keep == 0xFFFF and not beats[0].last
    assert beats[1].keep == 0xFFFF and not beats[1].last
    assert beats[2].keep == 0x01FF and beats[2].last
    assert unpack_axis_beats(beats, expected_kind=AeadStreamKind.TEXT, expected_len=len(data), bus_bytes=16) == data


def test_pack_empty_stream_uses_length_register_not_zero_byte_beat() -> None:
    assert pack_axis_beats(b"", AeadStreamKind.AD, bus_bytes=16) == ()
    assert unpack_axis_beats((), expected_kind=AeadStreamKind.AD, expected_len=0, bus_bytes=16) == b""


def test_unpack_rejects_partial_nonfinal_beat() -> None:
    bad = (
        AxisStreamBeat(data=b"A" * 16, keep=0x00FF, last=False, kind=AeadStreamKind.TEXT),
        AxisStreamBeat(data=b"B" * 16, keep=0x0001, last=True, kind=AeadStreamKind.TEXT),
    )
    with pytest.raises(ValueError, match="only the final beat"):
        unpack_axis_beats(bad, expected_kind=AeadStreamKind.TEXT, bus_bytes=16)


def test_axis_aead128_encrypt_matches_scalar_model_beyond_old_32_byte_limit() -> None:
    key = patterned(16, 0x10)
    nonce = patterned(16, 0x80)
    ad = patterned(97, 0x30)
    plaintext = patterned(149, 0x50)

    stream_result = axis_aead128_encrypt(
        key=key,
        nonce=nonce,
        ad_beats=pack_axis_beats(ad, AeadStreamKind.AD),
        plaintext_beats=pack_axis_beats(plaintext, AeadStreamKind.TEXT),
        ad_len=len(ad),
        text_len=len(plaintext),
    )
    scalar = ascon_aead128_encrypt(key, nonce, ad, plaintext)

    assert stream_result.ciphertext == scalar.ciphertext
    assert stream_result.tag == scalar.tag
    assert unpack_axis_beats(stream_result.ciphertext_beats, expected_kind=AeadStreamKind.TEXT, expected_len=len(plaintext)) == scalar.ciphertext


def test_axis_aead128_decrypt_buffers_plaintext_until_tag_valid() -> None:
    key = patterned(16, 0x01)
    nonce = patterned(16, 0x44)
    ad = patterned(65, 0xA0)
    plaintext = patterned(80, 0x11)
    enc = ascon_aead128_encrypt(key, nonce, ad, plaintext)

    dec = axis_aead128_decrypt(
        key=key,
        nonce=nonce,
        ad_beats=pack_axis_beats(ad, AeadStreamKind.AD),
        ciphertext_beats=pack_axis_beats(enc.ciphertext, AeadStreamKind.TEXT),
        ad_len=len(ad),
        text_len=len(enc.ciphertext),
        tag=enc.tag,
    )
    assert dec.valid
    assert dec.plaintext == plaintext
    assert ascon_aead128_decrypt(key, nonce, ad, enc.ciphertext, enc.tag).valid

    bad_tag = enc.tag[:-1] + bytes([enc.tag[-1] ^ 0x80])
    bad = axis_aead128_decrypt(
        key=key,
        nonce=nonce,
        ad_beats=pack_axis_beats(ad, AeadStreamKind.AD),
        ciphertext_beats=pack_axis_beats(enc.ciphertext, AeadStreamKind.TEXT),
        ad_len=len(ad),
        text_len=len(enc.ciphertext),
        tag=bad_tag,
    )
    assert not bad.valid
    assert bad.plaintext == b""
    assert bad.plaintext_beats == ()
