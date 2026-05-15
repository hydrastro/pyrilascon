from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_axis_headers_and_top_exist() -> None:
    defs = ROOT / "rtl" / "common" / "ascon_accel_axis_defs.vh"
    top = ROOT / "rtl" / "common" / "ascon_accel_axis_aead128_top.v"
    assert defs.is_file()
    assert top.is_file()
    assert "ASCON_AXIS_USER_AD" in defs.read_text()
    assert "ASCON_AXIS_USER_TEXT" in defs.read_text()
    text = top.read_text()
    assert "module ascon_accel_axis_aead128_top" in text
    assert "s_axis_tdata" in text
    assert "s_axis_tkeep" in text
    assert "s_axis_tvalid" in text
    assert "s_axis_tready" in text
    assert "m_axis_tdata" in text
    assert "m_axis_tvalid" in text
    assert "m_axis_tready" in text


def test_axis_top_preserves_frozen_control_plane_and_uses_stream_for_payload() -> None:
    text = (ROOT / "rtl" / "common" / "ascon_accel_axis_aead128_top.v").read_text()
    assert "ascon_accel_mmio_regs" in text
    assert "ascon_aead128_mmio_backend" in text
    assert "ASCON_CAP_AXI_STREAM_DATA" in text
    assert "AXIS input has priority" in text
    assert "axis_in_fire_w" in text
    assert "axis_out_fire_w" in text
    assert "output_active_q" in text


def test_axis_capability_generated_for_c_and_verilog() -> None:
    c_header = (ROOT / "firmware" / "ascon_accel" / "ascon_accel_regs.h").read_text()
    v_header = (ROOT / "rtl" / "common" / "ascon_accel_regs.vh").read_text()
    doc = (ROOT / "docs" / "ascon_accel_register_map.md").read_text()
    assert "ASCON_CAP_AXI_STREAM_DATA" in c_header
    assert "ASCON_CAP_AXI_STREAM_DATA" in v_header
    assert "AXI_STREAM_DATA" in doc


def test_axis_file_list_and_docs_exist() -> None:
    file_list = ROOT / "rtl" / "common" / "ascon_axis_file_list.f"
    doc = ROOT / "docs" / "axi_stream_data_plane.md"
    assert file_list.is_file()
    assert doc.is_file()
    fl = file_list.read_text()
    assert "ascon_accel_axis_defs.vh" in fl
    assert "ascon_accel_axis_aead128_top.v" in fl
    d = doc.read_text()
    assert "MMIO/CSR" in d
    assert "AXI Stream" in d
    assert "buffer-until-verify" in d
