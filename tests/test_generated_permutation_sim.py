"""Generated permutation cores must be bit-exact with the golden model.

Covers all three emitted families (round-based, fully-pipelined, column-serial).
Skipped automatically when Icarus Verilog is unavailable, like the rest of the
RTL sim suite; when present, each core is compiled and simulated against the
model's NIST-verified combinational p6/p8/p12.
"""
import pytest

from ascon_designspace.generator.permutation import ROUND_BASED_RPC
from ascon_designspace.generator.serial import COLUMN_SERIAL_COLUMNS
from ascon_designspace.generator.verify import (
    iverilog_available,
    verify_bit_serial,
    verify_column_serial,
    verify_permutation,
    verify_pipeline,
)

pytestmark = pytest.mark.skipif(not iverilog_available(), reason="iverilog/vvp not installed")


@pytest.mark.parametrize("rounds_per_cycle", sorted(set(ROUND_BASED_RPC.values())))
def test_round_based_core_matches_golden_model(rounds_per_cycle: int) -> None:
    passed, trials, line = verify_permutation(rounds_per_cycle)
    assert passed, f"R={rounds_per_cycle}: {line}"
    assert trials >= 100


@pytest.mark.parametrize("num_rounds", [6, 8, 12])
def test_pipelined_core_matches_golden_model(num_rounds: int) -> None:
    # Streams inputs at one/cycle, so this checks correctness AND throughput.
    passed, trials, line = verify_pipeline(num_rounds)
    assert passed, f"p{num_rounds}: {line}"
    assert trials >= 100


@pytest.mark.parametrize("columns_per_cycle", COLUMN_SERIAL_COLUMNS)
def test_column_serial_core_matches_golden_model(columns_per_cycle: int) -> None:
    passed, trials, line = verify_column_serial(columns_per_cycle)
    assert passed, f"K={columns_per_cycle}: {line}"
    assert trials >= 100


def test_bit_serial_core_matches_golden_model() -> None:
    passed, trials, line = verify_bit_serial()
    assert passed, line
    assert trials >= 100
