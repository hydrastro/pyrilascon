from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECRYPT_BACKEND = ROOT / "rtl" / "stream" / "ascon_aead128_stream_decrypt_buffered.v"
FILE_LIST = ROOT / "rtl" / "stream" / "ascon_stream_decrypt_file_list.f"
DOC = ROOT / "docs" / "streaming_aead_decrypt_buffered_backend.md"


def test_stream_decrypt_backend_files_exist() -> None:
    assert DECRYPT_BACKEND.is_file()
    assert FILE_LIST.is_file()
    assert DOC.is_file()


def test_stream_decrypt_backend_exposes_buffered_auth_interface() -> None:
    text = DECRYPT_BACKEND.read_text(encoding="utf-8")
    assert "module ascon_aead128_stream_decrypt_buffered" in text
    assert "parameter integer DATA_BYTES     = 16" in text
    assert "parameter integer MAX_TEXT_BYTES = 1024" in text
    assert "input  wire [127:0]            expected_tag_i" in text
    assert "output reg  [DATA_WIDTH-1:0]   m_axis_tdata" in text
    assert "plain_buf_q" in text
    assert "MAX_TEXT_BITS" in text


def test_stream_decrypt_backend_rejects_encrypt_mode_and_large_buffers() -> None:
    text = DECRYPT_BACKEND.read_text(encoding="utf-8")
    assert "mode_i != `ASCON_MODE_AEAD128 || !decrypt_i" in text
    assert "text_len_i > MAX_TEXT_BYTES" in text
    assert "`ASCON_ERROR_UNSUPPORTED_MODE" in text
    assert "`ASCON_ERROR_BAD_LENGTH" in text


def test_stream_decrypt_backend_never_releases_plaintext_before_auth() -> None:
    text = DECRYPT_BACKEND.read_text(encoding="utf-8")
    auth_idx = text.index("ST_AUTH_DECIDE")
    out_idx = text.index("ST_OUT_EMIT")
    assert auth_idx < out_idx
    assert "If authentication fails, no plaintext beat is emitted" in text
    assert "plain_buf_q <= set_plain_block" in text
    assert "m_axis_tvalid <= 1'b1" in text[out_idx:]
    assert "generated_tag_o == expected_tag_i" in text
    assert "plain_buf_q <= {MAX_TEXT_BITS{1'b0}}" in text


def test_stream_decrypt_backend_contains_tag_invalid_path() -> None:
    text = DECRYPT_BACKEND.read_text(encoding="utf-8")
    assert "ST_FINISH_FAIL" in text
    assert "tag_valid_o <= 1'b0" in text
    assert "error_o <= 1'b1" in text
    assert "error_code_o <= `ASCON_ERROR_TAG_INVALID" in text
    assert "m_axis_tvalid <= 1'b0" in text


def test_stream_decrypt_backend_uses_same_stream_validation_contract() -> None:
    text = DECRYPT_BACKEND.read_text(encoding="utf-8")
    for token in [
        "input_keep_contiguous_w",
        "input_keep_nonzero_w",
        "input_kind_ad_w",
        "input_kind_text_w",
        "ad_length_error_w",
        "text_length_error_w",
        "ASCON_ERROR_STREAM_PROTOCOL",
    ]:
        assert token in text


def test_stream_decrypt_file_list_orders_dependencies() -> None:
    lines = [line.strip() for line in FILE_LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines == [
        "rtl/common/ascon_accel_regs.vh",
        "rtl/common/ascon_accel_axis_defs.vh",
        "rtl/common/ascon_round_comb.v",
        "rtl/stream/ascon_aead128_stream_decrypt_buffered.v",
    ]


def test_stream_decrypt_backend_doc_records_quarantine_policy() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "must not expose plaintext until the tag has been verified" in text
    assert "internal quarantine buffer" in text
    assert "MAX_TEXT_BYTES" in text
    assert "m_axis_tvalid remains low" in text
    assert "ASCON_ERROR_TAG_INVALID" in text


def test_stream_decrypt_backend_avoids_verilog_reserved_formal_names() -> None:
    text = DECRYPT_BACKEND.read_text(encoding="utf-8")
    assert "input [MAX_TEXT_BITS-1:0] buf;" not in text
    assert "input [MAX_TEXT_BITS-1:0] plain_buf;" in text
    assert "plain_buf[(byte_offset + k) * 8 +: 8]" in text
