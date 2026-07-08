"""The AXI-Stream Ascon-AEAD128 accelerator must match the model.

Streams associated data then message on an AXI-Stream slave port, collects the
ciphertext/plaintext on an AXI-Stream master port, and checks it plus the tag
and validity flag against the NIST-verified model - for encrypt, decrypt
round-trip, and corrupted-tag rejection, across empty/partial/aligned/
multi-block lengths. Skips without iverilog.
"""
import pytest

from ascon_designspace.generator.verify import iverilog_available, verify_aead128_axis

pytestmark = pytest.mark.skipif(not iverilog_available(), reason="iverilog/vvp not installed")


def test_aead128_axis_matches_model():
    passed, trials, line = verify_aead128_axis()
    assert passed, line
    assert trials >= 20
