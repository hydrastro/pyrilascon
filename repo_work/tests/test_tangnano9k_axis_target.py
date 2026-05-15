from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "boards" / "tangnano9k" / "ascon_aead128_axis_slow"


def test_tangnano9k_axis_target_files_exist() -> None:
    assert (TARGET / "Makefile").is_file()
    assert (TARGET / "README.md").is_file()
    assert (TARGET / "tangnano9k_ascon_aead128_axis_slow.cst").is_file()
    assert (TARGET / "rtl" / "tangnano9k_ascon_aead128_axis_slow_top.v").is_file()


def test_tangnano9k_axis_target_uses_axis_top() -> None:
    makefile = (TARGET / "Makefile").read_text()
    top = (TARGET / "rtl" / "tangnano9k_ascon_aead128_axis_slow_top.v").read_text()
    assert "ascon_accel_axis_aead128_top.v" in makefile
    assert "ascon_accel_axis_aead128_top dut_i" in top
    assert "s_axis_tvalid" in top
    assert "m_axis_tready" in top
    assert "ASCON_AXIS_USER_AD" in top
    assert "ASCON_AXIS_USER_TEXT" in top


def test_fpga_max_throughput_decisions_documented() -> None:
    doc = (ROOT / "docs" / "fpga_max_throughput_decisions.md").read_text()
    assert "AXI4-Stream" in doc
    assert "128-bit payload path" in doc
    assert "multi-context interleaving" in doc
    assert "Tang Nano 9K targets are validation milestones" in doc
