"""Board flow: descriptor loading, target emission, and the exact build-command
shapes. No hardware required. A yosys-gated test elaborates the generated demo
to prove it is structurally synthesizable.
"""
import shutil
import subprocess

import pytest

from ascon_boards import build as B
from ascon_boards import list_boards
from ascon_boards.targets import emit_target, list_targets


def test_board_and_target_listed() -> None:
    assert "tangnano9k" in list_boards()
    assert "perm_smoke" in list_targets()


def test_tangnano9k_descriptor() -> None:
    b = B.load_board("tangnano9k")
    assert b.device == "GW1NR-LV9QN88PC6/I5"
    assert b.family == "GW1N-9C"
    assert b.freq_mhz == 27
    assert b.loader == "tangnano9k"
    assert b.constraints.name == "tangnano9k.cst"
    assert b.constraints.exists()


def test_emit_perm_smoke_uses_generated_core(tmp_path) -> None:
    built = emit_target("perm_smoke", tmp_path)
    assert built.top_module == "tangnano9k_perm_smoke"
    assert built.sources and all(s.exists() for s in built.sources)
    top = next(s for s in built.sources if "smoke" in s.name).read_text()
    # the flashed thing is generated RTL, self-checked against the model
    assert "ascon_perm_iter_r" in top
    assert "GOLDEN_P12" in top


def test_build_command_shapes(tmp_path) -> None:
    b = B.load_board("tangnano9k")
    built = emit_target("perm_smoke", tmp_path)

    syn, json_out = B.synth_command(b, built, tmp_path)
    syn_str = " ".join(syn)
    assert syn[0] == "yosys"
    assert "synth_gowin" in syn_str
    assert built.top_module in syn_str
    assert json_out.suffix == ".json"

    pnr, pnr_out = B.pnr_command(b, built, tmp_path, json_out)
    pnr_str = " ".join(pnr)
    assert b.device in pnr_str
    assert b.family in pnr_str
    assert str(b.constraints) in pnr_str
    assert str(b.freq_mhz) in pnr_str

    pack, fs = B.pack_command(b, built, tmp_path, pnr_out)
    assert pack[:3] == ["gowin_pack", "-d", b.family]
    assert fs.suffix == ".fs"

    assert B.flash_command(b, fs) == ["openFPGALoader", "-b", "tangnano9k", str(fs)]
    assert "-f" in B.flash_command(b, fs, to_flash=True)


def test_himbaechel_variant_shape(tmp_path) -> None:
    # A board asking for nextpnr-himbaechel gets the --vopt form.
    b = B.load_board("tangnano9k")
    b = B.Board(**{**b.__dict__, "nextpnr": "nextpnr-himbaechel"})
    built = emit_target("perm_smoke", tmp_path)
    _, json_out = B.synth_command(b, built, tmp_path)
    pnr, _ = B.pnr_command(b, built, tmp_path, json_out)
    pnr_str = " ".join(pnr)
    assert pnr[0] == "nextpnr-himbaechel"
    assert f"family={b.family}" in pnr_str
    assert f"cst={b.constraints}" in pnr_str


@pytest.mark.skipif(shutil.which("yosys") is None, reason="yosys not installed")
def test_perm_smoke_elaborates(tmp_path) -> None:
    built = emit_target("perm_smoke", tmp_path)
    incs = " ".join(f"-I {d}" for d in built.include_dirs)
    srcs = " ".join(str(s) for s in built.sources)
    result = subprocess.run(
        ["yosys", "-q", "-p", f"read_verilog {incs} {srcs}; hierarchy -check -top {built.top_module}"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr[-800:]


def test_tangnano20k_board_himbaechel_internal_reset():
    """The Tang Nano 20K board loads, uses the himbaechel PnR variant, and its
    generated smoke top has no rst_n port (power-on reset)."""
    from ascon_boards.build import load_board, pnr_command
    from ascon_boards.targets import emit_target

    board = load_board("tangnano20k")
    assert board.nextpnr == "nextpnr-himbaechel"
    assert board.reset_style == "internal"
    assert board.device == "GW2AR-LV18QN88C8/I7"

    import tempfile, pathlib as _pl
    with tempfile.TemporaryDirectory() as d:
        built = emit_target("perm_smoke", d, board=board)
        top_src = next(pl for pl in built.sources if pl.name.endswith("_perm_smoke.v")).read_text()
        assert "rst_n" not in top_src.split(");", 1)[0]   # no rst_n in the port list
        assert "por" in top_src                            # power-on reset present
        cmd, _ = pnr_command(board, built, _pl.Path(d), _pl.Path(d) / "x.json")
        assert "--vopt" in cmd and f"family={board.family}" in cmd
