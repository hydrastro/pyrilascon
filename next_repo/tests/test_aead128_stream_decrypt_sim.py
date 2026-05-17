from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.run_stream_decrypt_vector import (
    ASCON_ERROR_TAG_INVALID,
    build_golden_vector,
    corrupt_tag,
    generate_testbench,
    int_literal_from_bytes_le,
    result_to_jsonable,
    run_vector,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "run_stream_decrypt_vector.py"
DOC = REPO_ROOT / "docs" / "streaming_aead_decrypt_simulation.md"


def test_stream_decrypt_tool_dry_run_reports_valid_release_vector() -> None:
    key = bytes(range(16))
    nonce = bytes(range(16, 32))
    ad = bytes.fromhex("aabbccddeeff")
    plaintext = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112")

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--dry-run",
            "--key-hex",
            key.hex(),
            "--nonce-hex",
            nonce.hex(),
            "--ad-hex",
            ad.hex(),
            "--plaintext-hex",
            plaintext.hex(),
        ],
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["matched"] is None
    assert payload["rtl"] is None
    assert payload["golden"]["valid"] is True
    assert payload["golden"]["plaintext_hex"] == plaintext.hex()
    assert payload["golden"]["released_plaintext_hex"] == plaintext.hex()
    assert payload["golden"]["ciphertext_beats"][0]["keep_hex"] == "ffff"
    assert payload["golden"]["ciphertext_beats"][-1]["keep_hex"] == "0007"


def test_stream_decrypt_tool_dry_run_reports_invalid_tag_suppression() -> None:
    key = bytes(range(16))
    nonce = bytes(range(16, 32))
    ad = b"metadata"
    plaintext = b"secret plaintext"

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--dry-run",
            "--corrupt-tag",
            "--key-hex",
            key.hex(),
            "--nonce-hex",
            nonce.hex(),
            "--ad-hex",
            ad.hex(),
            "--plaintext-hex",
            plaintext.hex(),
        ],
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["golden"]["valid"] is False
    assert payload["golden"]["plaintext_hex"] == plaintext.hex()
    assert payload["golden"]["released_plaintext_hex"] == ""
    assert payload["golden"]["plaintext_beats"] == []
    assert payload["golden"]["expected_tag_hex"] != payload["golden"]["computed_tag_hex"]


def test_generated_decrypt_testbench_encodes_expected_tag_and_ciphertext_input() -> None:
    key = bytes(range(16))
    nonce = bytes(range(16, 32))
    ad = bytes(range(1, 4))
    plaintext = bytes(range(32))
    golden = build_golden_vector(key, nonce, ad, plaintext)
    tb = generate_testbench(golden)

    assert "ascon_aead128_stream_decrypt_buffered" in tb
    assert f"128'h{int_literal_from_bytes_le(key)}" in tb
    assert f"128'h{int_literal_from_bytes_le(nonce)}" in tb
    assert f"128'h{int_literal_from_bytes_le(bytes.fromhex(golden.expected_tag_hex))}" in tb
    assert "decrypt_i = 1'b1" in tb
    assert "send_beat(128'h00000000000000000000000000030201, 16'h0007, 1'b1, 4'h1);" in tb
    assert "send_beat" in tb
    assert "DONE cycle=%0d tag_valid=%0d error=%0d error_code=%0d tag=%032x" in tb


def test_generated_decrypt_testbench_holds_axis_valid_until_ready_handshake() -> None:
    golden = build_golden_vector(
        bytes(range(16)),
        bytes(range(16, 32)),
        bytes.fromhex("aabbccddeeff"),
        bytes(range(32)),
    )
    tb = generate_testbench(golden)

    assert "AXI valid must remain asserted until a real valid/ready handshake" in tb
    task_body = tb.split("task send_beat;", 1)[1].split("endtask", 1)[0]
    assert "while (!s_axis_tready) begin" in task_body
    assert task_body.index("s_axis_tvalid = 1'b1;") < task_body.index("while (!s_axis_tready) begin")
    assert task_body.index("while (!s_axis_tready) begin") < task_body.index("s_axis_tvalid = 1'b0;")


def test_stream_decrypt_simulation_doc_records_optional_simulator_flow() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "tools/run_stream_decrypt_vector.py" in text
    assert "iverilog" in text
    assert "vvp" in text
    assert "valid tag" in text
    assert "corrupt tag" in text
    assert "plaintext suppression" in text


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog/vvp not installed")
def test_stream_decrypt_rtl_sim_releases_plaintext_for_valid_tag() -> None:
    result = run_vector(
        key=bytes(range(16)),
        nonce=bytes(range(16, 32)),
        associated_data=bytes.fromhex("aabbccddeeff"),
        plaintext=bytes.fromhex("000102030405060708090a0b0c0d0e0f101112"),
        repo_root=REPO_ROOT,
        dry_run=False,
    )

    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)
    assert result.rtl is not None
    assert result.rtl.tag_valid == 1
    assert result.rtl.error == 0
    assert result.rtl.error_code == 0
    assert result.rtl.plaintext_hex == result.golden.plaintext_hex
    assert result.rtl.generated_tag_hex == result.golden.computed_tag_hex


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog/vvp not installed")
def test_stream_decrypt_rtl_sim_suppresses_plaintext_for_invalid_tag() -> None:
    result = run_vector(
        key=bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
        nonce=bytes.fromhex("101112131415161718191a1b1c1d1e1f"),
        associated_data=b"metadata",
        plaintext=b"secret plaintext",
        corrupt_expected_tag=True,
        repo_root=REPO_ROOT,
        dry_run=False,
    )

    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)
    assert result.rtl is not None
    assert result.rtl.tag_valid == 0
    assert result.rtl.error == 1
    assert result.rtl.error_code == ASCON_ERROR_TAG_INVALID
    assert result.rtl.plaintext_hex == ""
    assert result.rtl.generated_tag_hex == result.golden.computed_tag_hex


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog/vvp not installed")
@pytest.mark.parametrize(
    ("ad", "plaintext"),
    [
        (b"", b""),
        (b"", b"hello"),
        (b"metadata", b""),
        (bytes(range(16)), bytes(range(16, 48))),
    ],
)
def test_stream_decrypt_rtl_sim_matches_python_golden_for_boundary_vectors(ad: bytes, plaintext: bytes) -> None:
    result = run_vector(
        key=bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
        nonce=bytes.fromhex("101112131415161718191a1b1c1d1e1f"),
        associated_data=ad,
        plaintext=plaintext,
        repo_root=REPO_ROOT,
        dry_run=False,
    )

    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)
