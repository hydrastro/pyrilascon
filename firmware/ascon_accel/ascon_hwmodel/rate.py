from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64

SUPPORTED_RATE_BYTES: tuple[int, int] = (8, 16)


def check_rate_bytes(rate_bytes: int) -> None:
    if rate_bytes not in SUPPORTED_RATE_BYTES:
        raise ValueError(f"rate_bytes must be one of {SUPPORTED_RATE_BYTES}, got {rate_bytes}")


def rate_bytes_from_state(state: AsconState, rate_bytes: int) -> bytes:
    check_rate_bytes(rate_bytes)
    return state.to_bytes()[:rate_bytes]


def rate_int_from_state(state: AsconState, rate_bytes: int) -> int:
    return int.from_bytes(rate_bytes_from_state(state, rate_bytes), "little")


def replace_rate_bytes(state: AsconState, block: bytes, rate_bytes: int) -> AsconState:
    check_rate_bytes(rate_bytes)
    if len(block) != rate_bytes:
        raise ValueError(f"rate block must be {rate_bytes} bytes, got {len(block)}")
    if rate_bytes == 8:
        return state.with_word(0, U64(int.from_bytes(block, "little")))
    low: U64 = U64(int.from_bytes(block[0:8], "little"))
    high: U64 = U64(int.from_bytes(block[8:16], "little"))
    return AsconState(low, high, state.x2, state.x3, state.x4)


def xor_rate_bytes(state: AsconState, block: bytes, rate_bytes: int) -> AsconState:
    check_rate_bytes(rate_bytes)
    if len(block) != rate_bytes:
        raise ValueError(f"rate block must be {rate_bytes} bytes, got {len(block)}")
    current: bytes = rate_bytes_from_state(state, rate_bytes)
    updated: bytes = bytes(left ^ right for left, right in zip(current, block, strict=True))
    return replace_rate_bytes(state, updated, rate_bytes)


def pad_position_mask(rate_bytes: int, valid_bytes: int) -> int:
    check_rate_bytes(rate_bytes)
    if valid_bytes < 0 or valid_bytes >= rate_bytes:
        raise ValueError(f"valid_bytes must satisfy 0 <= valid_bytes < {rate_bytes}")
    return 1 << (8 * valid_bytes)


def emit_verilog_rate_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon rate-lane helpers.",
            emit_verilog_rate_select_function(),
            emit_verilog_rate_replace_function(),
            emit_verilog_rate_xor_function(),
        )
    )


def emit_verilog_rate_select_function() -> str:
    return "\n".join(
        (
            "function [127:0] ascon_rate_select;",
            "  input [319:0] state;",
            "  input         rate128;",
            "  begin",
            "    ascon_rate_select = rate128 ? state[127:0] : {64'b0, state[63:0]};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_rate_replace_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_rate_replace;",
            "  input [319:0] state;",
            "  input [127:0] block;",
            "  input         rate128;",
            "  begin",
            "    ascon_rate_replace = rate128 ? {state[319:128], block[127:0]} : {state[319:64], block[63:0]};",
            "  end",
            "endfunction",
        )
    )


def emit_verilog_rate_xor_function() -> str:
    return "\n".join(
        (
            "function [319:0] ascon_rate_xor;",
            "  input [319:0] state;",
            "  input [127:0] block;",
            "  input         rate128;",
            "  begin",
            "    ascon_rate_xor = rate128 ? (state ^ {192'b0, block[127:0]}) : (state ^ {256'b0, block[63:0]});",
            "  end",
            "endfunction",
        )
    )
