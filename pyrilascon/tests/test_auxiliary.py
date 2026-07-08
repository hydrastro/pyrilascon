from ascon_hwmodel.bitstring import BitString, pad_bitstring, parse_bitstring
from ascon_hwmodel.byteops import (
    WordBytes64,
    bytes_to_u64_le,
    bytes_to_words64_le,
    pad_bytes,
    parse_bytes,
    u64_to_bytes_le,
)
from ascon_hwmodel.uint import U64
from ascon_hwmodel.verilog import emit_verilog_pad64_partial_function, emit_verilog_pad128_partial_function


def test_bitstring_from_bytes_is_lsb_first_inside_each_byte() -> None:
    bits: BitString = BitString.from_bytes(bytes([0x01, 0x02, 0x80]))
    assert bits.bit_string() == "10000000" "01000000" "00000001"
    assert bits.to_bytes() == bytes([0x01, 0x02, 0x80])


def test_parse_bitstring_full_block_and_empty_final_block() -> None:
    parsed = parse_bitstring(BitString.from_bytes(bytes(range(16))), 128)
    assert len(parsed.full_blocks) == 1
    assert len(parsed.full_blocks[0]) == 128
    assert len(parsed.final_block) == 0


def test_parse_bitstring_partial_final_block() -> None:
    parsed = parse_bitstring(BitString.from_bytes(b"abcde"), 32)
    assert len(parsed.full_blocks) == 1
    assert parsed.full_blocks[0].to_bytes() == b"abcd"
    assert parsed.final_block.to_bytes() == b"e"


def test_pad_bitstring_matches_append_one_then_zeros() -> None:
    padded: BitString = pad_bitstring(BitString.from_bits((1, 0, 1)), 8)
    assert padded.bit_string() == "10110000"


def test_pad_byte_aligned_64_bit_table_values() -> None:
    expected: list[int] = [
        0x0000_0000_0000_0001,
        0x0000_0000_0000_01FF,
        0x0000_0000_0001_FFFF,
        0x0000_0000_01FF_FFFF,
        0x0000_0001_FFFF_FFFF,
        0x0000_01FF_FFFF_FFFF,
        0x0001_FFFF_FFFF_FFFF,
        0x01FF_FFFF_FFFF_FFFF,
    ]
    for byte_count, expected_value in enumerate(expected):
        padded: bytes = pad_bytes(b"\xFF" * byte_count, 8)
        assert int.from_bytes(padded, "little") == expected_value


def test_parse_bytes_full_block_and_empty_final_block() -> None:
    parsed = parse_bytes(bytes(range(16)), 16)
    assert parsed.full_blocks == (bytes(range(16)),)
    assert parsed.final_block == b""
    assert parsed.padded_final_block() == b"\x01" + (b"\x00" * 15)


def test_word_bytes_and_word_integer_conversion() -> None:
    word: U64 = bytes_to_u64_le(bytes(range(8)))
    assert word == U64(0x0706_0504_0302_0100)
    assert u64_to_bytes_le(word) == bytes(range(8))
    assert WordBytes64.from_u64(word).to_u64() == word
    assert bytes_to_words64_le(bytes(range(16))) == (
        U64(0x0706_0504_0302_0100),
        U64(0x0F0E_0D0C_0B0A_0908),
    )


def test_verilog_pad_helpers_present() -> None:
    assert "ascon_pad64_partial" in emit_verilog_pad64_partial_function()
    assert "valid_bytes * 8" in emit_verilog_pad64_partial_function()
    assert "ascon_pad128_partial" in emit_verilog_pad128_partial_function()
