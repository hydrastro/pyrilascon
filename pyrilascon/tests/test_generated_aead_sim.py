"""Generated AEAD cores must match the model across the whole variant family.

Each variant composes the generated permutation into a full Ascon AEAD datapath
(rate 8 or 16, p6 or p8, 128- or 160-bit key) and is checked on encrypt
(ciphertext+tag), decrypt round-trip, and corrupted-tag rejection, across AD/
message lengths from empty to multi-block. Skips without iverilog.
"""
import pytest

from ascon_designspace.generator.verify import iverilog_available, verify_aead

pytestmark = pytest.mark.skipif(not iverilog_available(), reason="iverilog/vvp not installed")


@pytest.mark.parametrize("variant", ["aead128", "aead128a", "ascon128", "aead80pq"])
def test_generated_aead_matches_model(variant):
    passed, trials, line = verify_aead(variant)
    assert passed, f"{variant}: {line}"
    assert trials >= 20
