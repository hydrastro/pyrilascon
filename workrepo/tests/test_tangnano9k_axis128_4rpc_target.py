from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "boards" / "tangnano9k" / "ascon_aead128_axis128_4rpc"
COMMON = ROOT / "rtl" / "common"


def test_axis128_4rpc_board_target_files_exist() -> None:
    assert (TARGET / "Makefile").is_file()
    assert (TARGET / "README.md").is_file()
    assert (TARGET / "tangnano9k_ascon_aead128_axis128_4rpc.cst").is_file()
    assert (TARGET / "rtl" / "tangnano9k_ascon_aead128_axis128_4rpc_top.v").is_file()


def test_axis128_4rpc_common_rtl_files_exist() -> None:
    for name in [
        "ascon_round4_comb.v",
        "ascon_aead128_mmio_backend_4rpc.v",
        "ascon_accel_axis128_aead128_4rpc_top.v",
        "ascon_axis128_4rpc_file_list.f",
    ]:
        assert (COMMON / name).is_file()


def test_axis128_4rpc_makefile_uses_128bit_top_and_round4() -> None:
    text = (TARGET / "Makefile").read_text()
    assert "tangnano9k_ascon_aead128_axis128_4rpc_top" in text
    assert "ascon_round4_comb.v" in text
    assert "ascon_aead128_mmio_backend_4rpc.v" in text
    assert "ascon_accel_axis128_aead128_4rpc_top.v" in text


def test_axis128_top_exposes_128bit_axis_and_4rpc_backend() -> None:
    text = (COMMON / "ascon_accel_axis128_aead128_4rpc_top.v").read_text()
    assert "input  wire [127:0] s_axis_tdata" in text
    assert "input  wire [15:0]  s_axis_tkeep" in text
    assert "output wire [127:0] m_axis_tdata" in text
    assert "output wire [15:0]  m_axis_tkeep" in text
    assert "ascon_aead128_mmio_backend_4rpc" in text


def test_round4_declares_four_round_candidate() -> None:
    text = (COMMON / "ascon_round4_comb.v").read_text()
    assert "module ascon_round4_comb" in text
    assert text.count("ascon_round_comb") == 4


def test_4rpc_backend_completes_p8_p12_with_expected_start_indices() -> None:
    text = (COMMON / "ascon_aead128_mmio_backend_4rpc.v").read_text()
    assert "rc_index_q <= 4'd4" in text
    assert "rc_index_q <= 4'd8" in text
    assert "if (rc_index_q == 4'd12)" in text
    assert "rc_index_q <= rc_index_q + 4'd4" in text
