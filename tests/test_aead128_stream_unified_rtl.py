from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "rtl" / "stream" / "ascon_aead128_stream.v"
FILE_LIST = ROOT / "rtl" / "stream" / "ascon_stream_file_list.f"
DOC = ROOT / "docs" / "streaming_aead_unified_backend.md"


def test_unified_stream_backend_files_exist() -> None:
    assert WRAPPER.is_file()
    assert FILE_LIST.is_file()
    assert DOC.is_file()


def test_unified_stream_backend_exposes_soc_facing_interface() -> None:
    text = WRAPPER.read_text(encoding="utf-8")
    assert "module ascon_aead128_stream" in text
    assert "parameter integer DATA_BYTES     = 16" in text
    assert "parameter integer MAX_TEXT_BYTES = 1024" in text
    assert "input  wire                    decrypt_i" in text
    assert "input  wire [127:0]            expected_tag_i" in text
    assert "output wire [127:0]            generated_tag_o" in text
    assert "output wire                    s_axis_tready" in text
    assert "output wire                    m_axis_tvalid" in text


def test_unified_stream_backend_dispatches_encrypt_and_decrypt_start_pulses() -> None:
    text = WRAPPER.read_text(encoding="utf-8")
    assert "assign start_encrypt_w = start_i && !decrypt_i;" in text
    assert "assign start_decrypt_w = start_i && decrypt_i;" in text
    assert "ascon_aead128_stream_encrypt" in text
    assert "ascon_aead128_stream_decrypt_buffered" in text
    assert ".start_i(start_encrypt_w)" in text
    assert ".start_i(start_decrypt_w)" in text
    assert ".decrypt_i(1'b0)" in text
    assert ".decrypt_i(1'b1)" in text


def test_unified_stream_backend_latches_selected_operation() -> None:
    text = WRAPPER.read_text(encoding="utf-8")
    assert "reg op_decrypt_q;" in text
    assert "op_decrypt_q <= decrypt_i;" in text
    assert "else if (start_i)" in text
    assert "assign s_axis_tready = op_decrypt_q ? dec_s_axis_tready_w : enc_s_axis_tready_w;" in text


def test_unified_stream_backend_muxes_data_and_status_outputs() -> None:
    text = WRAPPER.read_text(encoding="utf-8")
    for signal in [
        "m_axis_tdata",
        "m_axis_tkeep",
        "m_axis_tvalid",
        "m_axis_tlast",
        "m_axis_tuser",
        "busy_o",
        "done_o",
        "tag_valid_o",
        "error_o",
        "error_code_o",
        "generated_tag_o",
    ]:
        assert f"assign {signal}" in text
        assert "op_decrypt_q ? dec_" in text or signal == "s_axis_tready"


def test_unified_stream_file_list_orders_dependencies() -> None:
    lines = [line.strip() for line in FILE_LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines == [
        "rtl/common/ascon_accel_regs.vh",
        "rtl/common/ascon_accel_axis_defs.vh",
        "rtl/common/ascon_round_comb.v",
        "rtl/stream/ascon_aead128_stream_encrypt.v",
        "rtl/stream/ascon_aead128_stream_decrypt_buffered.v",
        "rtl/stream/ascon_aead128_stream.v",
    ]


def test_unified_stream_backend_doc_records_policy_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "SoC-facing AXI Stream AEAD128 backend" in text
    assert "decrypt_i = 0" in text
    assert "decrypt_i = 1" in text
    assert "Plaintext is released" in text
    assert "ASCON_ERROR_TAG_INVALID" in text
    assert "firmware, NEORV32 CFS wrapper, DMA frontend" in text
