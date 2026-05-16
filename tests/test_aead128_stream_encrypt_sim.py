from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ascon_hwmodel.aead_stream import AeadStreamKind, axis_aead128_encrypt, pack_axis_beats
from tools.run_stream_encrypt_vector import (
    build_golden_vector,
    generate_testbench,
    int_literal_from_bytes_le,
    run_vector,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "run_stream_encrypt_vector.py"
DOC = REPO_ROOT / "docs" / "streaming_aead_simulation.md"


def test_stream_encrypt_tool_dry_run_reports_python_golden_vector() -> None:
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
    expected = axis_aead128_encrypt(
        key=key,
        nonce=nonce,
        ad_beats=pack_axis_beats(ad, AeadStreamKind.AD),
        plaintext_beats=pack_axis_beats(plaintext, AeadStreamKind.TEXT),
        ad_len=len(ad),
        text_len=len(plaintext),
    )

    assert payload["matched"] is None
    assert payload["rtl"] is None
    assert payload["golden"]["ciphertext_hex"] == expected.ciphertext.hex()
    assert payload["golden"]["tag_hex"] == expected.tag.hex()
    assert payload["golden"]["ad_beats"][0]["keep_hex"] == "003f"
    assert payload["golden"]["plaintext_beats"][-1]["keep_hex"] == "0007"


def test_generated_testbench_encodes_little_endian_bus_literals() -> None:
    key = bytes(range(16))
    nonce = bytes(range(16, 32))
    ad = bytes(range(1, 4))
    plaintext = bytes(range(32))
    golden = build_golden_vector(key, nonce, ad, plaintext)
    tb = generate_testbench(golden)

    assert "ascon_aead128_stream_encrypt" in tb
    assert f"128'h{int_literal_from_bytes_le(key)}" in tb
    assert f"128'h{int_literal_from_bytes_le(nonce)}" in tb
    assert "send_beat(128'h00000000000000000000000000030201, 16'h0007, 1'b1, 4'h1);" in tb
    assert "send_beat(128'h0f0e0d0c0b0a09080706050403020100, 16'hffff, 1'b0, 4'h2);" in tb
    assert "send_beat(128'h1f1e1d1c1b1a19181716151413121110, 16'hffff, 1'b1, 4'h2);" in tb



def test_generated_testbench_holds_axis_valid_until_ready_handshake() -> None:
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

def test_stream_encrypt_simulation_doc_records_optional_simulator_flow() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "tools/run_stream_encrypt_vector.py" in text
    assert "iverilog" in text
    assert "vvp" in text
    assert "Python golden" in text
    assert "ciphertext" in text
    assert "tag" in text


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog/vvp not installed")
def test_stream_encrypt_rtl_sim_matches_python_golden_for_partial_final_blocks() -> None:
    result = run_vector(
        key=bytes(range(16)),
        nonce=bytes(range(16, 32)),
        associated_data=bytes.fromhex("aabbccddeeff"),
        plaintext=bytes.fromhex("000102030405060708090a0b0c0d0e0f101112"),
        repo_root=REPO_ROOT,
        dry_run=False,
    )

    assert result.matched is True
    assert result.rtl is not None
    assert result.rtl.error == 0
    assert result.rtl.error_code == 0
    assert result.rtl.ciphertext_hex == result.golden.ciphertext_hex
    assert result.rtl.tag_hex == result.golden.tag_hex


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
def test_stream_encrypt_rtl_sim_matches_python_golden_for_boundary_vectors(ad: bytes, plaintext: bytes) -> None:
    result = run_vector(
        key=bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
        nonce=bytes.fromhex("101112131415161718191a1b1c1d1e1f"),
        associated_data=ad,
        plaintext=plaintext,
        repo_root=REPO_ROOT,
        dry_run=False,
    )

    assert result.matched is True
