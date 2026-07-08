"""The Wishbone/XBUS adapter must complete NEORV32-style transactions and carry
the full AEAD register protocol correctly. NEORV32's XBUS drives STB as a single
pulse and holds CYC until ACK, sampling ACK only in the following cycle - this
test drives the adapter exactly that way and checks encrypt / decrypt / tag-reject
against the model. It is the regression guard for the on-board bus handshake.
Skips without iverilog.
"""
import pytest

from ascon_designspace.generator.verify import iverilog_available, verify_aead128_wb

pytestmark = pytest.mark.skipif(not iverilog_available(), reason="iverilog/vvp not installed")


def test_aead128_wb_xbus_matches_model():
    passed, trials, line = verify_aead128_wb()
    assert passed, line
    assert trials >= 20
