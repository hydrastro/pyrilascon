"""RTL co-simulation tests for the Ascon hash/XOF/CXOF backend.

Each test vector exercises one combination of variant + payload length
through the actual Verilog backend (``rtl/common/ascon_hash_xof_backend.v``)
and compares its output bit-for-bit against the Python golden model
(``ascon_hwmodel.hash_xof``).

The harness uses ``tools/run_hash_xof_vector.py`` which builds a small
per-vector Icarus Verilog testbench, runs it, and parses the result.

Coverage targets:
  * Hash256: empty, partial block, exact rate, multi-block
  * XOF128: variable output lengths
  * CXOF128: customisation-only, message-only, both
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "run_hash_xof_vector.py"
RTL = REPO_ROOT / "rtl" / "common" / "ascon_hash_xof_backend.v"


pytestmark = pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="Icarus Verilog (iverilog/vvp) not available",
)


def _run_vector(args: list[str]) -> dict:
    import json
    completed = subprocess.run(
        [sys.executable, str(TOOL)] + args,
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_rtl_source_present():
    assert RTL.exists(), f"hash backend source missing at {RTL}"


# ─── Hash256 ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "message_hex,label",
    [
        ("",                                            "empty"),
        ("41",                                          "one_byte"),
        ("41414141",                                    "four_byte_partial"),
        ("4141414141414141",                            "exact_rate_8B"),
        ("4141414141414141ff",                          "rate_plus_1"),
        ("000102030405060708090a0b0c0d0e0f10",          "multi_block_17B"),
        ("00" * 32,                                     "four_full_blocks"),
    ],
)
def test_hash256_matches_golden(message_hex: str, label: str) -> None:
    result = _run_vector(
        ["--variant", "hash256", "--message-hex", message_hex],
    )
    assert result["matched"], (
        f"hash256({label}) mismatch:\n"
        f"  golden = {result['golden']['digest_hex']}\n"
        f"  rtl    = {result['rtl']['digest_hex']}"
    )


# ─── XOF128 ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "message_hex,out_bytes,label",
    [
        ("",         16,  "empty_out16"),
        ("",         32,  "empty_out32"),
        ("deadbeef", 16,  "4B_out16"),
        ("deadbeef", 24,  "4B_out24_squeeze_grows"),
        ("00" * 16,  32,  "16B_out32"),
    ],
)
def test_xof128_matches_golden(message_hex: str, out_bytes: int, label: str) -> None:
    result = _run_vector(
        ["--variant", "xof128", "--message-hex", message_hex, "--out-bytes", str(out_bytes)],
    )
    assert result["matched"], (
        f"xof128({label}) mismatch:\n"
        f"  golden = {result['golden']['digest_hex']}\n"
        f"  rtl    = {result['rtl']['digest_hex']}"
    )


# ─── CXOF128 ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "message_hex,customisation_hex,out_bytes,label",
    [
        ("",         "",                  16, "both_empty"),
        ("78",       "",                  16, "msg_only_1B"),
        ("",         "68656c6c6f",        16, "cust_only_hello"),
        ("78797a77", "61626364",          16, "msg_4B_cust_4B"),
        ("00" * 8,   "ff" * 4,            16, "exact_rate_msg"),
    ],
)
def test_cxof128_matches_golden(
    message_hex: str, customisation_hex: str, out_bytes: int, label: str,
) -> None:
    result = _run_vector(
        [
            "--variant", "cxof128",
            "--message-hex", message_hex,
            "--customisation-hex", customisation_hex,
            "--out-bytes", str(out_bytes),
        ],
    )
    assert result["matched"], (
        f"cxof128({label}) mismatch:\n"
        f"  golden = {result['golden']['digest_hex']}\n"
        f"  rtl    = {result['rtl']['digest_hex']}"
    )
