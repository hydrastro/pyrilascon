from pathlib import Path

from ascon_hwmodel.iv import IV_PARAMS
from ascon_hwmodel.state import AsconState
from ascon_hwmodel.variants import AsconVariant
from ascon_hwmodel.verilog import render_verilog_files, write_verilog_files


def test_verilog_snippets_live_with_model_objects() -> None:
    assert IV_PARAMS[AsconVariant.AEAD128].verilog_expr() == "{16'h0000, 8'd16, 16'd128, 4'd8, 4'd12, 8'h00, 8'd1}"
    assert AsconState.verilog_pack_expr("x0", "x1", "x2", "x3", "x4") == "{x4, x3, x2, x1, x0}"
    assert AsconState.verilog_word_slice(0) == "state[63:0]"
    assert AsconState.verilog_word_slice(4) == "state[319:256]"


def test_render_verilog_files_uses_verilog_extensions_and_split_permutation_files() -> None:
    files = render_verilog_files()
    assert "ascon_model.vh" in files
    assert "ascon_permutation_comb.v" in files
    assert "ascon_p6_comb.v" in files
    assert "ascon_p8_comb.v" in files
    assert "ascon_p12_comb.v" in files
    assert all(name.endswith((".v", ".vh")) for name in files)
    assert '`include "ascon_pc.vh"' in files["ascon_model.vh"]
    assert '`include "ascon_ps.vh"' in files["ascon_model.vh"]
    assert '`include "ascon_pl.vh"' in files["ascon_model.vh"]
    assert '`include "ascon_p6.vh"' in files["ascon_model.vh"]
    assert '`include "ascon_p8.vh"' in files["ascon_model.vh"]
    assert '`include "ascon_p12.vh"' in files["ascon_model.vh"]
    assert "module ascon_permutation_comb" in files["ascon_permutation_comb.v"]
    assert "module ascon_p6_comb" in files["ascon_p6_comb.v"]


def test_write_verilog_files(tmp_path: Path) -> None:
    written = write_verilog_files(tmp_path)
    names = {path.name for path in written}
    assert "ascon_iv.vh" in names
    assert "ascon_ps.vh" in names
    assert "ascon_p6_comb.v" in names
    assert "ascon_p8_comb.v" in names
    assert "ascon_p12_comb.v" in names
    assert (tmp_path / "ascon_model.vh").read_text(encoding="utf-8").startswith('`include "ascon_iv.vh"')
