"""Generated sponge hash/XOF cores must match NIST-verified model output.

Covers Hash256 (fixed 256-bit), XOF128 (extendable output, tested at two
word-aligned lengths), and CXOF128 (customized XOF) - each composing the
generated permutation. Skips without iverilog.
"""
import pytest

from ascon_designspace.generator.verify import (
    iverilog_available,
    verify_cxof128,
    verify_hash256,
    verify_hasha,
    verify_xof128,
    verify_xofa,
)

pytestmark = pytest.mark.skipif(not iverilog_available(), reason="iverilog/vvp not installed")


def test_generated_hash256_matches_model():
    passed, trials, line = verify_hash256()
    assert passed, line
    assert trials >= 8


@pytest.mark.parametrize("out_bytes", [32, 40])
def test_generated_xof128_matches_model(out_bytes):
    passed, trials, line = verify_xof128(out_bytes)
    assert passed, f"xof {out_bytes}B: {line}"
    assert trials >= 8


def test_generated_cxof128_matches_model():
    passed, trials, line = verify_cxof128()
    assert passed, line
    assert trials >= 6


def test_generated_hasha_matches_reference():
    passed, trials, line = verify_hasha()
    assert passed, line
    assert trials >= 8


@pytest.mark.parametrize("out_bytes", [32, 40])
def test_generated_xofa_matches_reference(out_bytes):
    passed, trials, line = verify_xofa(out_bytes)
    assert passed, f"xofa {out_bytes}B: {line}"
    assert trials >= 8
