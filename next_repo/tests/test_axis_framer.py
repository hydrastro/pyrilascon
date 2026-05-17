from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAMER = ROOT / "rtl" / "stream" / "ascon_axis_framer.v"
CONTRACT = ROOT / "docs" / "streaming_aead_contract.md"


def test_streaming_aead_contract_documents_frozen_rules() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "control plane" in text
    assert "tkeep must be contiguous" in text
    assert "Only the final beat may be partial" in text
    assert "zero-length stream has no beats" in text
    assert "buffer-until-verify" in text
    assert "ascon_hwmodel.aead_stream" in text


def test_axis_framer_module_exists_and_exposes_reusable_interface() -> None:
    text = FRAMER.read_text(encoding="utf-8")
    assert "module ascon_axis_framer" in text
    assert "parameter integer DATA_BYTES = 16" in text
    assert "expected_len_i" in text
    assert "expected_user_i" in text
    assert "s_axis_tdata" in text
    assert "s_axis_tkeep" in text
    assert "s_axis_tlast" in text
    assert "s_axis_tuser" in text
    assert "block_data_o" in text
    assert "block_bytes_o" in text
    assert "bytes_seen_o" in text


def test_axis_framer_checks_stream_protocol_errors() -> None:
    text = FRAMER.read_text(encoding="utf-8")
    assert "is_contiguous_keep" in text
    assert "keep_nonzero_w" in text
    assert "kind_ok_w" in text
    assert "partial_w" in text
    assert "overflow_w" in text
    assert "exact_end_without_last_w" in text
    assert "short_final_w" in text
    assert "ASCON_ERROR_STREAM_PROTOCOL" in text


def test_axis_framer_handles_empty_stream_on_start_without_dummy_beat() -> None:
    text = FRAMER.read_text(encoding="utf-8")
    assert "expected_len_i == 32'h00000000" in text
    assert "done_o" in text
    assert "start_i" in text


def test_axis_framer_reuses_frozen_axis_and_error_definitions() -> None:
    text = FRAMER.read_text(encoding="utf-8")
    assert '`include "ascon_accel_regs.vh"' in text
    assert '`include "ascon_accel_axis_defs.vh"' in text
    assert "ASCON_AXIS_USER_NONE" in text
    assert "ASCON_ERROR_NONE" in text
    assert "ASCON_ERROR_STREAM_PROTOCOL" in text
