"""The SLINK/AXI-Stream data plane, checked against the golden model.

Same discipline as the rest of the suite: the expected values come from
ascon_hwmodel (which passes the official NIST KATs), never from the RTL itself.
This drives ascon_aead128_slink_mmio the way the SoC does -- control over the
register interface, payload as a plain word stream on the SLINK TX port,
ciphertext captured off the SLINK RX port.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="iverilog/vvp not installed",
)


def test_slink_data_plane_matches_model() -> None:
    """Encrypt and decrypt across 12 payload shapes through the stream plane."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_slink_plane.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    assert result.returncode == 0, f"SLINK plane verification failed:\n{result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout, result.stdout
