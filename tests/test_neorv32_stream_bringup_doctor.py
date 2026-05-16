from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT / "tools"))
from neorv32_stream_bringup_doctor import build_report, render_markdown, render_text  # noqa: E402
from prepare_neorv32_stream_board_build import prepare_package  # noqa: E402
from prepare_neorv32_stream_gowin_handoff import prepare_handoff  # noqa: E402


def _fake_neorv32(tmp_path: Path) -> Path:
    home = tmp_path / "neorv32"
    common = home / "sw" / "common"
    common.mkdir(parents=True)
    (common / "common.mk").write_text("# fake common.mk\n", encoding="utf-8")
    return home


def test_bringup_doctor_rejects_placeholder_neorv32_home(tmp_path: Path) -> None:
    package = tmp_path / "package"
    handoff = tmp_path / "handoff"
    prepare_package(package, clean=True)
    prepare_handoff(out_dir=handoff, package_dir=package, clean=True)

    report = build_report(
        neorv32_home=Path("/path/to/neorv32"),
        serial_device=None,
        package_dir=package,
        handoff_dir=handoff,
    )

    assert report["ready"] is False
    assert report["neorv32_home"]["is_placeholder"] is True
    assert any("placeholder" in blocker for blocker in report["blockers"])


def test_bringup_doctor_accepts_minimal_neorv32_checkout(tmp_path: Path) -> None:
    package = tmp_path / "package"
    handoff = tmp_path / "handoff"
    prepare_package(package, clean=True)
    prepare_handoff(out_dir=handoff, package_dir=package, clean=True)
    neorv32_home = _fake_neorv32(tmp_path)

    report = build_report(
        neorv32_home=neorv32_home,
        serial_device=None,
        package_dir=package,
        handoff_dir=handoff,
    )

    assert report["neorv32_home"]["ready"] is True
    assert report["package"]["package_json"] is True
    assert report["handoff"]["handoff_json"] is True
    assert report["handoff"]["uart_capture_script"] is True
    assert "auto-detection" in "\n".join(report["next_actions"])


def test_bringup_doctor_renderers_include_actionable_fields(tmp_path: Path) -> None:
    report = build_report(
        neorv32_home=Path("/path/to/neorv32"),
        serial_device=tmp_path / "missing_ttyUSB0",
        package_dir=tmp_path / "missing_package",
        handoff_dir=tmp_path / "missing_handoff",
    )

    text = render_text(report)
    md = render_markdown(report)

    assert "NEORV32_HOME" in text
    assert "serial" in text
    assert "Blockers" in md
    assert "Next actions" in md


def test_bringup_doctor_cli_writes_default_reports(tmp_path: Path) -> None:
    package = tmp_path / "package"
    handoff = tmp_path / "handoff"
    prepare_package(package, clean=True)
    prepare_handoff(out_dir=handoff, package_dir=package, clean=True)
    neorv32_home = _fake_neorv32(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "tools/neorv32_stream_bringup_doctor.py",
            "--neorv32-home",
            str(neorv32_home),
            "--package-dir",
            str(package),
            "--handoff-dir",
            str(handoff),
            "--write-defaults",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["name"] == "tangnano9k_neorv32_stream_bringup_doctor"
    assert (REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "bringup_doctor.json").exists()
    assert (REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "bringup_doctor.md").exists()


def test_bringup_doctor_cli_check_fails_on_blockers(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "tools/neorv32_stream_bringup_doctor.py",
            "--neorv32-home",
            "/path/to/neorv32",
            "--package-dir",
            str(tmp_path / "missing_package"),
            "--handoff-dir",
            str(tmp_path / "missing_handoff"),
            "--check",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "placeholder" in completed.stdout


def test_flake_includes_uart_capture_tools() -> None:
    flake = (REPO_ROOT / "flake.nix").read_text(encoding="utf-8")
    assert "picocom" in flake
    assert "usbutils" in flake


def test_root_and_board_makefiles_expose_bringup_doctor_and_uart_capture() -> None:
    root = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    board = (REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile").read_text(encoding="utf-8")

    assert "neorv32-stream-bringup-doctor" in root
    assert "neorv32-stream-uart-capture" in root
    assert "doctor:" in board
    assert "uart-capture:" in board


def test_gowin_handoff_firmware_script_rejects_placeholder_and_checks_common_mk(tmp_path: Path) -> None:
    package = tmp_path / "package"
    handoff = tmp_path / "handoff"
    prepare_package(package, clean=True)
    prepare_handoff(out_dir=handoff, package_dir=package, clean=True)

    firmware_script = handoff / "scripts" / "02_build_firmware.sh"
    uart_script = handoff / "scripts" / "05_capture_uart.sh"
    firmware_text = firmware_script.read_text(encoding="utf-8")
    uart_text = uart_script.read_text(encoding="utf-8")

    assert "tools/ensure_neorv32_checkout.py --print-home" in firmware_text
    assert "riscv-none-elf-gcc" in firmware_text
    assert "tools/capture_neorv32_uart.py" in uart_text
    assert "--serial-device" in uart_text
    assert os.access(uart_script, os.X_OK)
