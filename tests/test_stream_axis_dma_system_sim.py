import json
import shutil
from pathlib import Path

import pytest

from tools.run_stream_axis_dma_system_vector import (
    AD_BASE_BYTES,
    CSR_CONTROL_START,
    DATA_BYTES,
    DMA_CTRL_GO,
    DST_BASE_BYTES,
    MEM_WORDS,
    TEXT_BASE_BYTES,
    build_golden_vector,
    bytes_to_words_le,
    generate_testbench,
    result_to_jsonable,
    run_vector,
    words_to_bytes_le,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

_HAVE_IVERILOG = shutil.which("iverilog") is not None and shutil.which("vvp") is not None
_requires_iverilog = pytest.mark.skipif(not _HAVE_IVERILOG, reason="iverilog/vvp not installed")


def test_stream_axis_dma_system_dry_run_builds_golden_vector() -> None:
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
    # "hello" is five bytes -> two little-endian words in the source layout.
    assert result.golden.plaintext_words == bytes_to_words_le(b"hello")
    assert result.golden.ad_words == bytes_to_words_le(bytes.fromhex("aabbccddeeff"))


def test_word_packing_round_trips() -> None:
    payload = bytes(range(37))  # not a multiple of four, exercises tail padding
    words = bytes_to_words_le(payload)
    assert len(words) == (len(payload) + 3) // 4
    assert words_to_bytes_le(words, len(payload)) == payload


def test_descriptor_regions_are_disjoint_and_fit_memory() -> None:
    # AD, plaintext, and destination must not overlap and must fit the model.
    assert AD_BASE_BYTES < TEXT_BASE_BYTES < DST_BASE_BYTES
    assert DST_BASE_BYTES + 1024 <= MEM_WORDS * 4


def test_build_golden_rejects_oversize_plaintext() -> None:
    with pytest.raises(ValueError, match="MAX_TEXT_BYTES"):
        build_golden_vector(
            key=bytes(range(16)),
            nonce=bytes(range(16, 32)),
            associated_data=b"",
            plaintext=bytes(1025),
        )


def test_generated_dma_testbench_drives_csr_and_descriptor_windows() -> None:
    vector = build_golden_vector(
        key=bytes(range(16)),
        nonce=bytes(range(16, 32)),
        associated_data=b"metadata",
        plaintext=bytes(range(DATA_BYTES + 5)),
    )
    tb = generate_testbench(vector)

    assert "ascon_accel_stream_aead128_axis_dma_system #(" in tb
    assert "task csr_write" in tb
    assert "task dma_write" in tb
    # The autonomous transfer is kicked off by CSR START then descriptor GO.
    assert f"csr_write(8'h00, 32'h{CSR_CONTROL_START:08x});" in tb
    assert f"dma_write(8'h14, 32'h{DMA_CTRL_GO:08x});" in tb
    # The testbench embeds a synchronous memory model with byte-strobed writes.
    assert "reg [31:0] mem [0:MEM_WORDS-1];" in tb
    assert "mem_req_wstrb[0]" in tb
    # The ciphertext is read back out of memory (not from a bridge FIFO).
    assert "OUT_DST" in tb
    assert "DMA_DONE" in tb
    assert "CSR_DONE" in tb


def test_dma_testbench_dumps_one_word_per_ciphertext_word() -> None:
    plaintext = bytes(range(DATA_BYTES * 2 + 7))  # 39 bytes -> 10 destination words
    vector = build_golden_vector(
        key=bytes(range(16)),
        nonce=bytes(range(16, 32)),
        associated_data=b"",
        plaintext=plaintext,
    )
    tb = generate_testbench(vector)
    assert tb.count("$display(\"OUT_DST") == (len(plaintext) + 3) // 4


def test_stream_axis_dma_system_cli_dry_run_includes_testbench() -> None:
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


@_requires_iverilog
def test_stream_axis_dma_system_rtl_sim_matches_python_for_empty_message() -> None:
    result = run_vector(
        key=bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
        nonce=bytes.fromhex("101112131415161718191a1b1c1d1e1f"),
        associated_data=b"",
        plaintext=b"",
        repo_root=REPO_ROOT,
        dry_run=False,
    )
    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)
    assert result.rtl is not None
    assert result.rtl.dma_out_bytes == 0


@_requires_iverilog
@pytest.mark.parametrize(
    ("ad", "plaintext"),
    [
        pytest.param(b"", b"hello", id="empty-ad-short-pt"),
        pytest.param(b"metadata", b"", id="short-ad-empty-pt"),
        pytest.param(bytes.fromhex("aabbccddeeff"), bytes.fromhex("0001020304050607"), id="partial-ad-short-pt"),
        pytest.param(b"", bytes(range(DATA_BYTES)), id="empty-ad-one-full-beat"),
        pytest.param(bytes(range(DATA_BYTES)), bytes(range(DATA_BYTES * 2)), id="one-ad-beat-two-text-beats"),
        pytest.param(bytes.fromhex("aabbccddeeff"), bytes(range(DATA_BYTES + 3)), id="partial-ad-partial-final-text"),
        pytest.param(bytes(range(DATA_BYTES * 2 + 5)), bytes(range(DATA_BYTES * 3)), id="multi-partial-ad-multi-text"),
    ],
)
def test_stream_axis_dma_system_rtl_sim_matches_python(ad: bytes, plaintext: bytes) -> None:
    result = run_vector(
        key=bytes(range(16)),
        nonce=bytes(range(16, 32)),
        associated_data=ad,
        plaintext=plaintext,
        repo_root=REPO_ROOT,
        dry_run=False,
    )
    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)
    assert result.rtl is not None
    assert result.rtl.dma_out_bytes == len(plaintext)


@_requires_iverilog
@pytest.mark.parametrize("beats", [8, 16, 64])
def test_stream_axis_dma_system_streams_beyond_cpu_bridge_fifo_depth(beats: int) -> None:
    # The CPU-driven AXI-MMIO bridge tops out at a four-beat RX FIFO; the DMA
    # streams ciphertext to memory beat by beat, so it handles long payloads
    # that the bridge smoke test cannot express.  This is the headline feature.
    plaintext = bytes((i * 37) & 0xFF for i in range(DATA_BYTES * beats))
    result = run_vector(
        key=bytes(range(16)),
        nonce=bytes(range(16, 32)),
        associated_data=b"context",
        plaintext=plaintext,
        repo_root=REPO_ROOT,
        dry_run=False,
    )
    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)
    assert result.rtl is not None
    assert result.rtl.dma_out_bytes == len(plaintext)
    assert result.rtl.ciphertext_hex == result.golden.ciphertext_hex
