from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64, U320
from ascon_hwmodel.verilog import emit_verilog_state_pack_function, emit_verilog_state_word_function


def example_state() -> AsconState:
    return AsconState(
        U64(0x0706_0504_0302_0100),
        U64(0x0F0E_0D0C_0B0A_0908),
        U64(0x1716_1514_1312_1110),
        U64(0x1F1E_1D1C_1B1A_1918),
        U64(0x2726_2524_2322_2120),
    )


def test_state_from_spec_byte_sequence_example() -> None:
    state: AsconState = AsconState.from_bytes(bytes(range(40)))
    assert state == example_state()
    assert state.to_bytes() == bytes(range(40))


def test_u320_round_trip_logical_little_endian() -> None:
    state: AsconState = example_state()
    packed: U320 = state.to_u320()
    assert packed.value == int(
        "2726252423222120"
        "1F1E1D1C1B1A1918"
        "1716151413121110"
        "0F0E0D0C0B0A0908"
        "0706050403020100",
        16,
    )
    assert AsconState.from_u320(packed) == state


def test_word_access_and_xor() -> None:
    state: AsconState = AsconState.zero()
    state = state.with_word(2, U64(0xAAAA_AAAA_AAAA_AAAA))
    assert state.word(2) == U64(0xAAAA_AAAA_AAAA_AAAA)
    state = state.xor_word(2, U64(0xFFFF_0000_FFFF_0000))
    assert state.word(2) == U64(0x5555_AAAA_5555_AAAA)


def test_verilog_state_helpers_use_logical_bit_indices() -> None:
    assert "ascon_state_pack = {x4, x3, x2, x1, x0};" in emit_verilog_state_pack_function()
    assert "3'd0: ascon_state_word = state[63:0];" in emit_verilog_state_word_function()
    assert "3'd4: ascon_state_word = state[319:256];" in emit_verilog_state_word_function()
