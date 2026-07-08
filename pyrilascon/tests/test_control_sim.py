"""The microcoded-sequencer permutation must match the model.

Same verified round datapath as the iterative core, but ROM-driven control
(the MICROCODED_SEQUENCER style). Checked against the model's p6/p8/p12.
Skips without iverilog.
"""
import pytest

from ascon_designspace.generator.verify import iverilog_available, verify_microcoded

pytestmark = pytest.mark.skipif(not iverilog_available(), reason="iverilog/vvp not installed")


def test_microcoded_permutation_matches_model():
    passed, trials, line = verify_microcoded()
    assert passed, line
    assert trials >= 100
