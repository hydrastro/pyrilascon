from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT / "tools"))
from prepare_neorv32_stream_board_build import prepare_package  # noqa: E402
from prepare_neorv32_stream_gowin_handoff import prepare_handoff, validate_handoff  # noqa: E402


def test_prepare_gowin_handoff_generates_expected_files(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    out_dir = tmp_path / "gowin_handoff"
    prepare_package(package_dir, clean=True)

    handoff = prepare_handoff(out_dir=out_dir, package_dir=package_dir, clean=True)

    assert handoff["name"] == "tangnano9k_neorv32_stream_axis_mmio_gowin_handoff"
    for generated in handoff["generated_files"]:
        assert (out_dir / generated).exists(), generated
    validate_handoff(out_dir)


def test_gowin_handoff_preserves_memory_map_and_firmware_mode(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    out_dir = tmp_path / "gowin_handoff"
    prepare_package(package_dir, clean=True)
    handoff = prepare_handoff(out_dir=out_dir, package_dir=package_dir, clean=True)

    assert handoff["memory_map"]["csr_base"] == "0xFFEB0000"
    assert handoff["memory_map"]["axis_mmio_base"] == "0xFFEB0100"
    assert handoff["firmware"]["make_mode"] == "USE_CFS_AXIS_MMIO=1"

    header = (out_dir / "firmware" / "ascon_stream_axis_mmio_config.h").read_text(encoding="utf-8")
    assert "ASCON_ACCEL_BASE_ADDR 0xFFEB0000u" in header
    assert "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR 0xFFEB0100u" in header


def test_gowin_handoff_splits_verilog_and_vhdl_sources(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    out_dir = tmp_path / "gowin_handoff"
    prepare_package(package_dir, clean=True)
    handoff = prepare_handoff(out_dir=out_dir, package_dir=package_dir, clean=True)

    verilog = (out_dir / "sources" / "rtl_sources_verilog.f").read_text(encoding="utf-8")
    vhdl = (out_dir / "sources" / "rtl_sources_vhdl.f").read_text(encoding="utf-8")

    assert "rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v" in verilog
    assert "rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd" in vhdl
    assert handoff["rtl"]["verilog_count"] > 0
    assert handoff["rtl"]["vhdl_count"] == 1


def test_gowin_handoff_scripts_are_executable_and_guarded(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    out_dir = tmp_path / "gowin_handoff"
    prepare_package(package_dir, clean=True)
    prepare_handoff(out_dir=out_dir, package_dir=package_dir, clean=True)

    firmware_script = out_dir / "scripts" / "02_build_firmware.sh"
    program_script = out_dir / "scripts" / "04_program_sram.sh"
    assert os.access(firmware_script, os.X_OK)
    assert os.access(program_script, os.X_OK)
    firmware_text = firmware_script.read_text(encoding="utf-8")
    preflight_text = (out_dir / "scripts" / "01_preflight.sh").read_text(encoding="utf-8")
    assert "NEORV32_HOME" in firmware_text
    assert "../../../.." in firmware_text
    assert "../../../.." in preflight_text
    assert "openFPGALoader -b tangnano9k" in program_script.read_text(encoding="utf-8")


def test_gowin_handoff_cli_json_and_check(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    out_dir = tmp_path / "gowin_handoff"
    prepare_package(package_dir, clean=True)

    result = subprocess.run(
        [
            sys.executable,
            "tools/prepare_neorv32_stream_gowin_handoff.py",
            "--package-dir",
            str(package_dir),
            "--out",
            str(out_dir),
            "--clean",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["name"] == "tangnano9k_neorv32_stream_axis_mmio_gowin_handoff"

    check = subprocess.run(
        [sys.executable, "tools/prepare_neorv32_stream_gowin_handoff.py", "--out", str(out_dir), "--check"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert check.stdout.strip() == "ok"


def test_root_makefile_exposes_gowin_handoff_target() -> None:
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "neorv32-stream-gowin-handoff" in text
    assert "prepare_neorv32_stream_gowin_handoff.py" in text


def test_board_makefile_exposes_gowin_handoff_target() -> None:
    text = (REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile").read_text(encoding="utf-8")
    assert "gowin-handoff" in text
    assert "prepare_neorv32_stream_gowin_handoff.py" in text
