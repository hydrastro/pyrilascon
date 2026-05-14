from ascon_hwmodel.ps import SBOX, p_s_bitsliced, p_s_lut, sbox5_bits, sbox5_value
from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64


def test_sbox_bits_helper_matches_lut_encoding() -> None:
    for value, expected in enumerate(SBOX):
        bits = ((value >> 4) & 1, (value >> 3) & 1, (value >> 2) & 1, (value >> 1) & 1, value & 1)
        out_bits = sbox5_bits(*bits)
        out_value = 0
        for bit, shift in zip(out_bits, (4, 3, 2, 1, 0)):
            out_value |= bit << shift
        assert sbox5_value(value) == expected
        assert out_value == expected


def test_lut_and_bitsliced_substitution_layers_match() -> None:
    states = (
        AsconState.zero(),
        AsconState(U64(0), U64(1), U64(2), U64(3), U64(4)),
        AsconState(
            U64(0x0123_4567_89AB_CDEF),
            U64(0xFEDC_BA98_7654_3210),
            U64(0xFFFF_0000_FFFF_0000),
            U64(0x0000_FFFF_0000_FFFF),
            U64(0xA5A5_5A5A_A5A5_5A5A),
        ),
    )
    for state in states:
        assert p_s_lut(state) == p_s_bitsliced(state)
