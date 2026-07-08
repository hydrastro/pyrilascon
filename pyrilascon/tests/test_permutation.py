import pytest

from ascon_hwmodel.permutation import (
    MASK64,
    ROUND_CONSTANTS,
    SBOX,
    ascon_p6,
    ascon_p8,
    ascon_p12,
    p_c,
    p_l,
    p_s,
    rotr64,
    round_constant,
    round_constant_index,
    sbox5_value,
)
from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64


def _reference_sbox(value: int) -> int:
    x0 = (value >> 4) & 1
    x1 = (value >> 3) & 1
    x2 = (value >> 2) & 1
    x3 = (value >> 1) & 1
    x4 = value & 1
    y0 = (x4 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ (x1 & x0) ^ x1 ^ x0
    y1 = x4 ^ (x3 & x2) ^ (x3 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ x1 ^ x0
    y2 = (x4 & x3) ^ x4 ^ x2 ^ x1 ^ 1
    y3 = (x4 & x0) ^ x4 ^ (x3 & x0) ^ x3 ^ x2 ^ x1 ^ x0
    y4 = (x4 & x1) ^ x4 ^ x3 ^ (x1 & x0) ^ x1
    return (y0 << 4) | (y1 << 3) | (y2 << 2) | (y3 << 1) | y4


def test_round_constants_table_and_schedule() -> None:
    assert [c.value for c in ROUND_CONSTANTS] == [
        0x3C,
        0x2D,
        0x1E,
        0x0F,
        0xF0,
        0xE1,
        0xD2,
        0xC3,
        0xB4,
        0xA5,
        0x96,
        0x87,
        0x78,
        0x69,
        0x5A,
        0x4B,
    ]
    assert round_constant_index(12, 0) == 4
    assert round_constant_index(12, 11) == 15
    assert round_constant_index(8, 0) == 8
    assert round_constant_index(6, 0) == 10
    assert round_constant(6, 5) == U64(0x4B)


@pytest.mark.parametrize("bad_rounds", [0, 17])
def test_round_schedule_rejects_invalid_round_counts(bad_rounds: int) -> None:
    with pytest.raises(ValueError):
        round_constant_index(bad_rounds, 0)


def test_rotr64() -> None:
    assert rotr64(U64(0x8000_0000_0000_0001), 1) == U64(0xC000_0000_0000_0000)
    assert rotr64(U64(0x0123_4567_89AB_CDEF), 8) == U64(0xEF01_2345_6789_ABCD)


def test_sbox_table_matches_boolean_polynomial() -> None:
    for value, expected in enumerate(SBOX):
        assert sbox5_value(value) == expected
        assert _reference_sbox(value) == expected


def test_parallel_sbox_layer_matches_table_for_all_5bit_inputs() -> None:
    for value, expected in enumerate(SBOX):
        inputs = [(value >> shift) & 1 for shift in (4, 3, 2, 1, 0)]
        state = AsconState.from_words(tuple(U64(MASK64 if bit else 0) for bit in inputs))
        actual = p_s(state)
        output_bits = [1 if word.value == MASK64 else 0 for word in actual.words()]
        output_value = 0
        for bit, shift in zip(output_bits, (4, 3, 2, 1, 0)):
            output_value |= bit << shift
        assert output_value == expected


def test_constant_addition_touches_only_x2() -> None:
    state = AsconState(U64(1), U64(2), U64(3), U64(4), U64(5))
    actual = p_c(state, 12, 0)
    assert actual == AsconState(U64(1), U64(2), U64(3 ^ 0xF0), U64(4), U64(5))


def test_linear_layer_known_value() -> None:
    state = AsconState(
        U64(0x0123_4567_89AB_CDEF),
        U64(0x1020_3040_5060_7080),
        U64(0xFFFF_0000_FFFF_0000),
        U64(0x0000_FFFF_0000_FFFF),
        U64(0xA5A5_5A5A_A5A5_5A5A),
    )
    actual = p_l(state)
    assert actual == AsconState(
        U64(0xE222_7BB3_F333_6AA2),
        U64(0x1181_72A3_D343_B4E0),
        U64(0x83FF_7C00_83FF_7C00),
        U64(0x803F_7FC0_803F_7FC0),
        U64(0x3DBC_C243_3DBC_C243),
    )


def test_zero_state_permutation_regression_values() -> None:
    assert ascon_p6(AsconState.zero()).hex_words() == (
        "160C_84F2_0FAA_D4F1",
        "2149_5B1B_0AE3_3EEF",
        "E037_7D04_E23A_914B",
        "2B23_4815_98FF_A8EA",
        "649A_F379_BA83_CD30",
    )
    assert ascon_p8(AsconState.zero()).hex_words() == (
        "1418_F8AF_721A_A830",
        "A542_5F1F_8CB3_1388",
        "A01E_F761_BF8E_1652",
        "F01F_DABF_8C8A_82B4",
        "0168_260B_ADF7_6A06",
    )
    assert ascon_p12(AsconState.zero()).hex_words() == (
        "78EA_7AE5_CFEB_B108",
        "9B9B_FB85_13B5_60F7",
        "6937_F83E_03D1_1A50",
        "3FE5_3F36_F2C1_178C",
        "045D_648E_4DEF_12C9",
    )
