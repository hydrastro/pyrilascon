import json
import shutil
from pathlib import Path

import pytest

from tools.run_stream_axis_mmio_system_vector import (
    AXIS_STATUS_RX_VALID,
    AXIS_STATUS_TX_READY,
    CSR_CONTROL_START,
    DATA_BYTES,
    build_golden_vector,
    generate_testbench,
    result_to_jsonable,
    run_vector,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_stream_axis_mmio_system_dry_run_builds_golden_vector() -> None:
    result = run_vector(
        key=bytes(range(16)),
        nonce=bytes(range(16, 32)),
        associated_data=bytes.fromhex("aabbccddeeff"),
        plaintext=b"hello",
        repo_root=REPO_ROOT,
        dry_run=True,
    )

    assert result.matched is None
    assert result.rtl is None
    assert result.golden.ciphertext_hex
    assert len(bytes.fromhex(result.golden.tag_hex)) == 16
    assert len(result.golden.ad_beats) == 1
    assert len(result.golden.plaintext_beats) == 1
    assert len(result.golden.ciphertext_beats) == 1


def test_stream_axis_mmio_system_rejects_multibeat_smoke_vectors() -> None:
    with pytest.raises(ValueError, match="one AD beat and one text beat"):
        build_golden_vector(
            key=bytes(range(16)),
            nonce=bytes(range(16, 32)),
            associated_data=b"",
            plaintext=bytes(range(DATA_BYTES + 1)),
        )


def test_generated_stream_axis_mmio_system_testbench_drives_two_mmio_windows() -> None:
    vector = build_golden_vector(
        key=bytes(range(16)),
        nonce=bytes(range(16, 32)),
        associated_data=b"metadata",
        plaintext=b"hello",
    )
    tb = generate_testbench(vector)

    assert "ascon_accel_stream_aead128_axis_mmio_system dut" in tb
    assert "task csr_write" in tb
    assert "task axis_send_beat" in tb
    assert "csr_write(8'h00, 32'h00000001);" in tb  # CONTROL.START
    assert f"wait_axis_bits(32'h{AXIS_STATUS_TX_READY:08x});" in tb
    assert f"wait_axis_bits(32'h{AXIS_STATUS_RX_VALID:08x});" in tb
    assert "OUT_BEAT" in tb
    assert "DONE" in tb


def test_stream_axis_mmio_system_cli_dry_run_includes_testbench() -> None:
    result = run_vector(
        key=bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
        nonce=bytes.fromhex("101112131415161718191a1b1c1d1e1f"),
        associated_data=b"",
        plaintext=b"",
        repo_root=REPO_ROOT,
        dry_run=True,
        include_testbench=True,
    )
    payload = result_to_jsonable(result)
    assert payload["testbench"] is not None
    assert payload["golden"]["ciphertext_hex"] == ""


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog/vvp not installed")
def test_stream_axis_mmio_system_rtl_sim_matches_python_for_empty_message() -> None:
    result = run_vector(
        key=bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
        nonce=bytes.fromhex("101112131415161718191a1b1c1d1e1f"),
        associated_data=b"",
        plaintext=b"",
        repo_root=REPO_ROOT,
        dry_run=False,
    )
    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog/vvp not installed")
@pytest.mark.parametrize(
    ("ad", "plaintext"),
    [
        (b"", b"hello"),
        (b"metadata", b""),
        (bytes.fromhex("aabbccddeeff"), bytes.fromhex("0001020304050607")),
    ],
)
def test_stream_axis_mmio_system_rtl_sim_matches_python_for_one_beat_vectors(ad: bytes, plaintext: bytes) -> None:
    result = run_vector(
        key=bytes(range(16)),
        nonce=bytes(range(16, 32)),
        associated_data=ad,
        plaintext=plaintext,
        repo_root=REPO_ROOT,
        dry_run=False,
    )
    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)
