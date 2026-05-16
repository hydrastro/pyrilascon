import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "prepare_neorv32_stream_board_build.py"
ROOT_MAKEFILE = ROOT / "Makefile"
BOARD_MAKEFILE = ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile"
BOARD_README = ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "README.md"
DOC = ROOT / "docs" / "neorv32_stream_board_package.md"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_board_package_tool_writes_expected_handoff_files(tmp_path: Path) -> None:
    out = tmp_path / "package"
    result = run_tool("--out", str(out), "--clean")
    assert "wrote" in result.stdout

    expected = [
        "README.md",
        "manifest.json",
        "preflight.json",
        "package.json",
        "memory_map.json",
        "rtl_sources_all.f",
        "rtl_sources_verilog.f",
        "rtl_sources_vhdl.f",
        "firmware/neorv32_stream_defines.mk",
        "firmware/ascon_stream_axis_mmio_config.h",
        "commands.sh",
    ]
    for relpath in expected:
        assert (out / relpath).exists(), relpath


def test_board_package_json_records_sources_memory_and_firmware(tmp_path: Path) -> None:
    out = tmp_path / "package"
    result = run_tool("--out", str(out), "--clean", "--json")
    package = json.loads(result.stdout)

    assert package["schema_version"] == 1
    assert package["name"] == "tangnano9k_neorv32_stream_axis_mmio_package"
    assert package["memory_map"]["csr_base"] == "0xFFEB0000"
    assert package["memory_map"]["axis_mmio_base"] == "0xFFEB0100"
    assert package["firmware"]["make_mode"] == "USE_CFS_AXIS_MMIO=1"
    assert package["rtl"]["sources_total"] == len(package["rtl"]["verilog_sources"]) + len(package["rtl"]["vhdl_sources"])
    assert package["rtl"]["vhdl_sources"] == ["rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd"]


def test_board_package_check_validates_existing_package(tmp_path: Path) -> None:
    out = tmp_path / "package"
    run_tool("--out", str(out), "--clean")
    result = run_tool("--out", str(out), "--check")
    assert result.stdout.strip() == "ok"


def test_board_package_splits_mixed_language_file_lists(tmp_path: Path) -> None:
    out = tmp_path / "package"
    run_tool("--out", str(out), "--clean")

    all_sources = (out / "rtl_sources_all.f").read_text(encoding="utf-8").splitlines()
    verilog_sources = (out / "rtl_sources_verilog.f").read_text(encoding="utf-8").splitlines()
    vhdl_sources = (out / "rtl_sources_vhdl.f").read_text(encoding="utf-8").splitlines()

    assert len(all_sources) == len(verilog_sources) + len(vhdl_sources)
    assert "rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v" in verilog_sources
    assert "rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd" in vhdl_sources


def test_board_package_generates_firmware_config_files(tmp_path: Path) -> None:
    out = tmp_path / "package"
    run_tool("--out", str(out), "--clean")

    header = (out / "firmware" / "ascon_stream_axis_mmio_config.h").read_text(encoding="utf-8")
    mk = (out / "firmware" / "neorv32_stream_defines.mk").read_text(encoding="utf-8")

    assert "#define ASCON_BENCH_USE_AXIS_MMIO 1" in header
    assert "#define ASCON_ACCEL_BASE_ADDR 0xFFEB0000u" in header
    assert "#define ASCON_ACCEL_AXIS_MMIO_BASE_ADDR 0xFFEB0100u" in header
    assert "USE_CFS_AXIS_MMIO ?= 1" in mk
    assert "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR ?= 0xFFEB0100u" in mk


def test_board_package_commands_script_contains_preboard_sequence(tmp_path: Path) -> None:
    out = tmp_path / "package"
    run_tool("--out", str(out), "--clean")
    script = (out / "commands.sh").read_text(encoding="utf-8")

    assert "print_neorv32_stream_board_manifest.py --check" in script
    assert "neorv32_stream_board_preflight.py --check" in script
    assert "make stream-axis-mmio-system-sim" in script
    assert "make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware" in script


def test_makefiles_and_docs_expose_board_package_target() -> None:
    root_makefile = ROOT_MAKEFILE.read_text(encoding="utf-8")
    board_makefile = BOARD_MAKEFILE.read_text(encoding="utf-8")
    board_readme = BOARD_README.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "neorv32-stream-board-package:" not in root_makefile
    assert "package:" in board_makefile
    assert "prepare_neorv32_stream_board_build.py --out" in board_makefile
    assert "make package" in board_readme
    assert "make -C boards/tangnano9k/neorv32_stream_axis_mmio package" in doc
    assert "build/neorv32_stream_axis_mmio/package" in doc
