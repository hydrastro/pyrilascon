from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "boards" / "tangnano20k" / "neorv32_mmio"


def test_target_files_and_device_configuration() -> None:
    makefile = (BOARD / "Makefile").read_text(encoding="utf-8")
    top = (BOARD / "rtl" / "tangnano20k_neorv32_mmio_top.vhd").read_text(encoding="utf-8")
    constraints = (BOARD / "tangnano20k_neorv32_mmio.cst").read_text(encoding="utf-8")

    assert "GW2AR-LV18QN88C8/I7" in makefile
    assert "YOSYS_FAMILY := gw2a" in makefile
    assert "PNR_FAMILY := GW2A-18C" in makefile
    assert "FREQ_MHZ := 27" in makefile
    assert "synth_gowin -family $(YOSYS_FAMILY)" in makefile
    assert "--report \"$(PNR_REPORT)\"" in makefile
    assert "gowin_pack" in makefile
    assert "-b tangnano20k -f" in makefile

    assert "BOOT_MODE_SELECT => 2" in top
    assert "pre-initialized internal IMEM image" in top
    assert "RISCV_ISA_Zicntr  => true" in top
    assert "IMEM_SIZE        => 32*1024" in top
    assert "DMEM_SIZE        => 8*1024" in top

    for constraint in (
        'IO_LOC  "clk" 4;',
        'IO_LOC  "rst_n" 88;',
        'IO_LOC "uart_tx" 69;',
        'IO_LOC "uart_rx" 70;',
        'IO_LOC "led_n[0]" 15;',
        'IO_LOC "led_n[5]" 20;',
    ):
        assert constraint in constraints


def test_bitstream_cannot_race_or_use_stale_firmware() -> None:
    makefile = (BOARD / "Makefile").read_text(encoding="utf-8")

    assert "$(GHDL_V): $(FW_STAMP)" in makefile
    assert "$(FW_STAMP): $(FW_INPUTS)" in makefile
    assert "clean_all exe install" in makefile
    assert "ASCON_BENCH_BUILD_TAG=tangnano20k-neorv32-mmio" in makefile
    assert "NEORV32_ROM_SIZE=32k NEORV32_RAM_SIZE=8k" in makefile
    assert "prog-sram: bitstream" in makefile
    assert "upload:" not in makefile


def test_board_uses_complete_capture_and_canonical_strict_report() -> None:
    makefile = (BOARD / "Makefile").read_text(encoding="utf-8")
    capture = (ROOT / "tools" / "capture_neorv32_uart.py").read_text(encoding="utf-8")

    assert "tools/capture_neorv32_uart.py" in makefile
    assert "tools/parse_sweep_log.py" in makefile
    assert "--strict" in makefile
    assert "parse_neorv32_ascon_uart_log.py" not in makefile
    assert "tools/summarize_ascon_benchmark.py" not in makefile
    assert 'line == "PASS"' in capture
    assert "timed out" in capture


def test_flake_and_ignore_rules_prevent_board_local_dependency_copies() -> None:
    flake = (ROOT / "flake.nix").read_text(encoding="utf-8")
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "PYRILASCON_ROOT" in flake
    assert '$PYRILASCON_ROOT/.venv-fpga' in flake
    assert '$PYRILASCON_ROOT/external/neorv32' in flake
    assert "export NEORV32_HOME" not in flake
    assert "requirements-fpga.txt" in flake
    assert "/external/neorv32/" in ignore
    assert ".venv-*/" in ignore
