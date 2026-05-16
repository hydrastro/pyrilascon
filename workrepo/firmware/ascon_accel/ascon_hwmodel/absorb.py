from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64
from ascon_hwmodel.word import Block64, Block128


def absorb_block64_into_x0(state: AsconState, block: Block64) -> AsconState:
    """Absorb one 64-bit block into S[0:63], i.e. x0."""
    return state.with_word(0, U64(state.x0.value ^ block.value.value))


def absorb_block128_into_x0_x1(state: AsconState, block: Block128) -> AsconState:
    """Absorb one 128-bit block into S[0:127], i.e. x0 and x1."""
    low, high = block.words()
    return AsconState(
        U64(state.x0.value ^ low.value),
        U64(state.x1.value ^ high.value),
        state.x2,
        state.x3,
        state.x4,
    )
