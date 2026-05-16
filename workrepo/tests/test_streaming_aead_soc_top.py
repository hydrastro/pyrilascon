from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = ROOT / "rtl" / "common" / "ascon_accel_stream_aead128_top.v"
FILE_LIST = ROOT / "rtl" / "common" / "ascon_stream_aead128_top_file_list.f"
DOC = ROOT / "docs" / "streaming_aead_soc_top.md"


def test_streaming_aead_soc_top_files_exist() -> None:
    assert TOP.is_file()
    assert FILE_LIST.is_file()
    assert DOC.is_file()


def test_streaming_aead_soc_top_keeps_frozen_mmio_control_plane() -> None:
    text = TOP.read_text(encoding="utf-8")
    assert "module ascon_accel_stream_aead128_top" in text
    assert "ascon_accel_mmio_regs" in text
    for port in [
        "bus_valid_i",
        "bus_write_i",
        "bus_addr_i",
        "bus_wdata_i",
        "bus_wstrb_i",
        "bus_rdata_o",
        "bus_ready_o",
        "irq_o",
    ]:
        assert port in text
    assert ".core_start_o(core_start_w)" in text
    assert ".core_decrypt_o(core_decrypt_w)" in text
    assert ".core_expected_tag_o(core_expected_tag_w)" in text
    assert ".core_generated_tag_i(stream_generated_tag_w)" in text


def test_streaming_aead_soc_top_exposes_128_bit_axis_data_plane() -> None:
    text = TOP.read_text(encoding="utf-8")
    assert "parameter integer DATA_BYTES     = 16" in text
    assert "parameter integer DATA_WIDTH     = DATA_BYTES * 8" in text
    for signal in [
        "s_axis_tdata",
        "s_axis_tkeep",
        "s_axis_tvalid",
        "s_axis_tready",
        "s_axis_tlast",
        "s_axis_tuser",
        "m_axis_tdata",
        "m_axis_tkeep",
        "m_axis_tvalid",
        "m_axis_tready",
        "m_axis_tlast",
        "m_axis_tuser",
    ]:
        assert signal in text


def test_streaming_aead_soc_top_instantiates_unified_stream_backend() -> None:
    text = TOP.read_text(encoding="utf-8")
    assert "ascon_aead128_stream #(" in text
    assert "stream_backend_i" in text
    assert ".decrypt_i(core_decrypt_w)" in text
    assert ".expected_tag_i(core_expected_tag_w)" in text
    assert ".generated_tag_o(stream_generated_tag_w)" in text
    assert ".s_axis_tready(s_axis_tready)" in text
    assert ".m_axis_tvalid(m_axis_tvalid)" in text


def test_streaming_aead_soc_top_advertises_stream_capabilities() -> None:
    text = TOP.read_text(encoding="utf-8")
    for cap in [
        "`ASCON_CAP_AEAD128",
        "`ASCON_CAP_DECRYPT_BUFFERED",
        "`ASCON_CAP_CONSTTIME_TAG_COMPARE",
        "`ASCON_CAP_STREAMING_BYTEMASK",
        "`ASCON_CAP_CYCLE_COUNTER",
        "`ASCON_CAP_AXI_STREAM_DATA",
    ]:
        assert cap in text


def test_streaming_aead_soc_top_file_list_orders_dependencies() -> None:
    lines = [line.strip() for line in FILE_LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines == [
        "rtl/common/ascon_accel_regs.vh",
        "rtl/common/ascon_accel_axis_defs.vh",
        "rtl/common/ascon_round_comb.v",
        "rtl/common/ascon_accel_mmio_regs.v",
        "rtl/stream/ascon_aead128_stream_encrypt.v",
        "rtl/stream/ascon_aead128_stream_decrypt_buffered.v",
        "rtl/stream/ascon_aead128_stream.v",
        "rtl/common/ascon_accel_stream_aead128_top.v",
    ]


def test_streaming_aead_soc_top_doc_records_integration_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "firmware-facing top" in text
    assert "ascon_accel_stream_aead128_top" in text
    assert "CONTROL.DECRYPT = 0" in text
    assert "CONTROL.DECRYPT = 1" in text
    assert "ASCON_CAP_AXI_STREAM_DATA" in text
    assert "Bulk payload transfer must use AXI Stream" in text
    assert "New SoC, DMA, and NEORV32 integration work should" in text
