"""The driver-compatible MMIO peripheral must match the model when driven through
the firmware driver's exact register protocol (writes to CONTROL/MODE/KEY/NONCE/
lengths/TAG, START, DATA_IN/DATA_IN_CTRL streaming, STATUS polling, DATA_OUT/TAG
reads) - for encrypt, decrypt round-trip, and corrupted-tag rejection. This is
what makes the existing benchmark firmware drive the accelerator unchanged.
Skips without iverilog.
"""
import pytest

from ascon_designspace.generator.verify import iverilog_available, verify_aead128_axis_mmio

pytestmark = pytest.mark.skipif(not iverilog_available(), reason="iverilog/vvp not installed")


def test_aead128_axis_mmio_matches_model():
    passed, trials, line = verify_aead128_axis_mmio()
    assert passed, line
    assert trials >= 20
