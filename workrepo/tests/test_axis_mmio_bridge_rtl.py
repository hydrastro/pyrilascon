from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "rtl" / "common" / "ascon_axis_mmio_bridge.v"
SYSTEM = ROOT / "rtl" / "common" / "ascon_accel_stream_aead128_axis_mmio_system.v"
FILE_LIST = ROOT / "rtl" / "common" / "ascon_stream_aead128_axis_mmio_system_file_list.f"
DOC = ROOT / "docs" / "axis_mmio_bridge_rtl.md"


def test_axis_mmio_bridge_rtl_matches_firmware_register_contract() -> None:
    text = BRIDGE.read_text(encoding="utf-8")
    header = (ROOT / "firmware" / "ascon_accel" / "ascon_accel_axis_mmio_transport.h").read_text(
        encoding="utf-8"
    )

    assert "module ascon_axis_mmio_bridge" in text
    for name, value in [
        ("REG_TX_DATA0", "8'h00"),
        ("REG_TX_KEEP", "8'h10"),
        ("REG_TX_CTRL", "8'h18"),
        ("REG_STATUS", "8'h1c"),
        ("REG_RX_DATA0", "8'h20"),
        ("REG_RX_KEEP", "8'h30"),
        ("REG_RX_CTRL", "8'h38"),
    ]:
        assert name in text
        assert value in text

    assert "ASCON_AXIS_MMIO_TX_CTRL_VALID" in header
    assert "TX_CTRL_VALID = 32'h00000001" in text
    assert "STATUS_TX_READY = 32'h00000001" in text
    assert "STATUS_RX_VALID = 32'h00000002" in text
    assert "STATUS_RX_LAST  = 32'h00000004" in text
    assert "STATUS_ERROR    = 32'h80000000" in text
    assert "bits[15:8] RX_LEVEL" in text
    assert "RX_CTRL_POP     = 32'h00000001" in text


def test_axis_mmio_bridge_has_single_tx_hold_and_fifo_backed_rx() -> None:
    text = BRIDGE.read_text(encoding="utf-8")
    assert "parameter integer RX_FIFO_DEPTH = 4" in text
    assert "reg       tx_valid_q" in text
    assert "assign m_axis_tvalid = tx_valid_q" in text
    assert "wire tx_fire_w      = tx_valid_q & m_axis_tready" in text
    assert "reg [DATA_WIDTH-1:0] rx_data_fifo_q" in text
    assert "reg [RX_PTR_BITS-1:0] rx_rd_ptr_q" in text
    assert "reg [RX_PTR_BITS-1:0] rx_wr_ptr_q" in text
    assert "reg [RX_CNT_BITS-1:0] rx_count_q" in text
    assert "assign s_axis_tready = ~rx_fifo_full_w" in text
    assert "STATUS_RX_VALID" in text
    assert "rx_level_word_w" in text
    assert "RX_CTRL_POP" in text
    assert "error_q <= 1'b1" in text


def test_axis_mmio_system_wrapper_connects_bridge_to_stream_soc_top() -> None:
    text = SYSTEM.read_text(encoding="utf-8")
    assert "module ascon_accel_stream_aead128_axis_mmio_system" in text
    assert "csr_bus_valid_i" in text
    assert "axis_bus_valid_i" in text
    assert "ascon_axis_mmio_bridge" in text
    assert "ascon_accel_stream_aead128_top" in text
    assert ".m_axis_tdata(bridge_to_core_tdata_w)" in text
    assert ".s_axis_tdata(core_to_bridge_tdata_w)" in text
    assert ".s_axis_tdata(bridge_to_core_tdata_w)" in text
    assert ".m_axis_tdata(core_to_bridge_tdata_w)" in text
    assert "parameter integer RX_FIFO_DEPTH  = 4" in text
    assert ".RX_FIFO_DEPTH(RX_FIFO_DEPTH)" in text


def test_axis_mmio_system_file_list_contains_required_rtl_in_order() -> None:
    lines = [line.strip() for line in FILE_LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert "rtl/common/ascon_round_comb.v" in lines
    assert "rtl/common/ascon_accel_mmio_regs.v" in lines
    assert "rtl/stream/ascon_aead128_stream_encrypt.v" in lines
    assert "rtl/stream/ascon_aead128_stream_decrypt_buffered.v" in lines
    assert "rtl/stream/ascon_aead128_stream.v" in lines
    assert "rtl/common/ascon_accel_stream_aead128_top.v" in lines
    assert lines[-2:] == [
        "rtl/common/ascon_axis_mmio_bridge.v",
        "rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v",
    ]


def test_axis_mmio_bridge_rtl_documentation_mentions_two_mmio_windows() -> None:
    doc = DOC.read_text(encoding="utf-8")
    assert "ascon_axis_mmio_bridge" in doc
    assert "ASCON_ACCEL_BASE_ADDR" in doc
    assert "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR" in doc
    assert "TX_CTRL.VALID" in doc
    assert "RX_CTRL.POP" in doc
    assert "RX FIFO" in doc
    assert "DMA-fed AXI-stream frontend" in doc


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_axis_mmio_bridge_and_system_wrapper_compile_with_iverilog(tmp_path: Path) -> None:
    out = tmp_path / "axis_mmio_system.vvp"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-Wall",
            "-I",
            str(ROOT / "rtl" / "common"),
            "-I",
            str(ROOT / "rtl" / "stream"),
            "-o",
            str(out),
            str(ROOT / "rtl" / "common" / "ascon_round_comb.v"),
            str(ROOT / "rtl" / "common" / "ascon_accel_mmio_regs.v"),
            str(ROOT / "rtl" / "stream" / "ascon_aead128_stream_encrypt.v"),
            str(ROOT / "rtl" / "stream" / "ascon_aead128_stream_decrypt_buffered.v"),
            str(ROOT / "rtl" / "stream" / "ascon_aead128_stream.v"),
            str(ROOT / "rtl" / "common" / "ascon_accel_stream_aead128_top.v"),
            str(BRIDGE),
            str(SYSTEM),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert out.exists()
