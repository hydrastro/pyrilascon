from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STREAM_BACKEND = ROOT / "rtl" / "stream" / "ascon_aead128_stream_encrypt.v"
FRAMER = ROOT / "rtl" / "stream" / "ascon_axis_framer.v"
FILE_LIST = ROOT / "rtl" / "stream" / "ascon_stream_encrypt_file_list.f"
DOC = ROOT / "docs" / "streaming_aead_encrypt_backend.md"


def test_stream_encrypt_backend_files_exist() -> None:
    assert STREAM_BACKEND.is_file()
    assert FRAMER.is_file()
    assert FILE_LIST.is_file()
    assert DOC.is_file()


def test_stream_encrypt_backend_exposes_128bit_axis_native_interface() -> None:
    text = STREAM_BACKEND.read_text(encoding="utf-8")
    assert "module ascon_aead128_stream_encrypt" in text
    assert "parameter integer DATA_BYTES = 16" in text
    assert "input  wire [DATA_WIDTH-1:0]   s_axis_tdata" in text
    assert "input  wire [DATA_BYTES-1:0]   s_axis_tkeep" in text
    assert "output reg  [DATA_WIDTH-1:0]   m_axis_tdata" in text
    assert "output reg  [DATA_BYTES-1:0]   m_axis_tkeep" in text
    assert "m_axis_tuser <= `ASCON_AXIS_USER_TEXT" in text


def test_stream_encrypt_backend_uses_local_phase_receiver_for_ad_then_text() -> None:
    text = STREAM_BACKEND.read_text(encoding="utf-8")
    assert "The reusable ascon_axis_framer remains available" in text
    assert "assign s_axis_tready = ((state_q == ST_AD_WAIT) && (ad_len_i != 32'd0))" in text
    assert "input_kind_ad_w" in text
    assert "input_kind_text_w" in text
    assert "ad_seen_q" in text
    assert "text_seen_q" in text
    assert "ad_protocol_error_w" in text
    assert "text_protocol_error_w" in text


def test_stream_encrypt_backend_is_encrypt_only_and_rejects_decrypt() -> None:
    text = STREAM_BACKEND.read_text(encoding="utf-8")
    assert "decrypt_i" in text
    assert "mode_i != `ASCON_MODE_AEAD128 || decrypt_i" in text
    assert "`ASCON_ERROR_UNSUPPORTED_MODE" in text
    assert "tag_valid_o <= 1'b0" in text
    assert "generated_tag_o <= tag_calc_w" in text


def test_stream_encrypt_backend_contains_unbounded_block_scheduler_states() -> None:
    text = STREAM_BACKEND.read_text(encoding="utf-8")
    for state in [
        "ST_INIT_P12",
        "ST_AD_WAIT",
        "ST_AD_EMPTY",
        "ST_DOMAIN",
        "ST_TEXT_WAIT",
        "ST_TEXT_EMIT",
        "ST_TEXT_OUT_WAIT",
        "ST_TEXT_P8",
        "ST_TEXT_EMPTY",
        "ST_FINAL_P12",
    ]:
        assert state in text
    assert "MAX_AD_BYTES" not in text
    assert "MAX_TEXT_BYTES" not in text
    assert "ad_buf_q" not in text
    assert "text_buf_q" not in text


def test_stream_encrypt_backend_handles_exact_block_padding_cases() -> None:
    text = STREAM_BACKEND.read_text(encoding="utf-8")
    assert "ad_empty_after_full_q" in text
    assert "text_p8_after_last_full_q" in text
    assert "pad_block(128'h0, 5'd0)" in text
    assert "text_block_is_partial_final_w" in text
    assert "text_block_is_full_final_w" in text
    assert "text_block128_q <= input_block128_w" in text
    assert "m_axis_tdata <= ciphertext_block_w" in text


def test_stream_encrypt_file_list_orders_dependencies() -> None:
    lines = [line.strip() for line in FILE_LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines == [
        "rtl/common/ascon_accel_regs.vh",
        "rtl/common/ascon_accel_axis_defs.vh",
        "rtl/common/ascon_round_comb.v",
        "rtl/stream/ascon_axis_framer.v",
        "rtl/stream/ascon_aead128_stream_encrypt.v",
    ]


def test_stream_encrypt_backend_doc_records_boundaries() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "Unbounded encryption" in text
    assert "Intentionally not implemented" in text
    assert "Authenticated decrypt" in text
    assert "AD packet first, then plaintext packet" in text
    assert "do not require dummy AXI beats" in text
