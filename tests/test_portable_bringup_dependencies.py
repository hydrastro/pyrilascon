from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import capture_neorv32_uart  # noqa: E402
from capture_neorv32_uart import choose_serial  # noqa: E402
from ensure_neorv32_checkout import candidate_paths, is_neorv32_checkout, locate_neorv32  # noqa: E402
import neorv32_stream_bringup_doctor as doctor  # noqa: E402
from neorv32_stream_bringup_doctor import build_report  # noqa: E402
from prepare_neorv32_stream_board_build import prepare_package  # noqa: E402
from prepare_neorv32_stream_gowin_handoff import prepare_handoff  # noqa: E402


def _fake_neorv32(path: Path) -> Path:
    common = path / "sw" / "common"
    common.mkdir(parents=True)
    (common / "common.mk").write_text("# fake common.mk\n", encoding="utf-8")
    return path


def test_project_local_neorv32_checkout_is_auto_detected(tmp_path: Path) -> None:
    vendor = _fake_neorv32(tmp_path / "external" / "neorv32")

    status = locate_neorv32(vendor_dir=vendor)

    assert status["ready"] is True
    assert status["home"] == str(vendor)
    assert status["source"] == "project-local"
    assert is_neorv32_checkout(vendor)


def test_ensure_neorv32_cli_print_home_uses_project_local_checkout(tmp_path: Path) -> None:
    vendor = _fake_neorv32(tmp_path / "external" / "neorv32")

    completed = subprocess.run(
        [
            sys.executable,
            "tools/ensure_neorv32_checkout.py",
            "--vendor-dir",
            str(vendor),
            "--print-home",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == str(vendor)


def test_ensure_neorv32_cli_suggests_fetch_when_missing(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "tools/ensure_neorv32_checkout.py",
            "--vendor-dir",
            str(tmp_path / "missing"),
            "--check",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "make -C boards/tangnano9k/neorv32_stream_axis_mmio deps" in completed.stdout


def test_bringup_doctor_uses_project_local_neorv32_without_machine_specific_home(tmp_path: Path) -> None:
    package = tmp_path / "package"
    handoff = tmp_path / "handoff"
    prepare_package(package, clean=True)
    prepare_handoff(out_dir=handoff, package_dir=package, clean=True)
    vendor = _fake_neorv32(tmp_path / "external" / "neorv32")
    original_vendor_dir = doctor.DEFAULT_VENDOR_DIR
    doctor.DEFAULT_VENDOR_DIR = vendor
    try:
        report = build_report(neorv32_home=None, serial_device=None, package_dir=package, handoff_dir=handoff)
    finally:
        doctor.DEFAULT_VENDOR_DIR = original_vendor_dir

    assert report["neorv32_home"]["ready"] is True
    assert report["neorv32_home"]["source"] == "project-local"


def test_serial_capture_reports_candidates_and_does_not_require_hardcoded_ttyusb0(tmp_path: Path) -> None:
    missing = tmp_path / "ttyUSB-does-not-exist"

    status = choose_serial(missing)

    assert status["ready"] is False
    assert status["source"] == "explicit"
    assert "does not exist" in status["message"]
    assert isinstance(status["candidates"], list)


def test_board_makefile_exposes_portable_dependency_targets() -> None:
    makefile = (REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile").read_text(encoding="utf-8")
    root = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "ensure_neorv32_checkout.py" in makefile
    assert "tools/capture_neorv32_uart.py" in makefile
    assert "picocom -b" not in makefile
    assert "neorv32-stream-build-firmware" not in root


def test_handoff_scripts_use_portable_helpers(tmp_path: Path) -> None:
    package = tmp_path / "package"
    handoff = tmp_path / "handoff"
    prepare_package(package, clean=True)
    prepare_handoff(out_dir=handoff, package_dir=package, clean=True)

    firmware = (handoff / "scripts" / "02_build_firmware.sh").read_text(encoding="utf-8")
    uart = (handoff / "scripts" / "05_capture_uart.sh").read_text(encoding="utf-8")

    assert "tools/ensure_neorv32_checkout.py --print-home" in firmware
    assert "make -C boards/tangnano9k/neorv32_stream_axis_mmio deps" in firmware
    assert "tools/capture_neorv32_uart.py" in uart
    assert "SERIAL" in uart


def test_neorv32_auto_detection_does_not_probe_home_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    vendor = tmp_path / "external" / "neorv32"

    candidates = candidate_paths(vendor_dir=vendor)

    assert {item["source"] for item in candidates} == {"project-local"}
    assert all(str(tmp_path / "fake-home") not in item["path"] for item in candidates)


def test_board_makefile_does_not_pass_environment_home_path_implicitly() -> None:
    makefile = (REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile").read_text(encoding="utf-8")

    assert "NEORV32_ARG = $(if $(filter command line,$(origin NEORV32_HOME))" in makefile
    assert "--vendor-dir $(NEORV32_DIR) --print-home" in makefile
    assert "firmware-auto:" in makefile


def test_sipeed_by_id_serial_candidate_is_preferred_when_accessible(monkeypatch) -> None:
    candidates = [
        "/dev/serial/by-id/usb-SIPEED_JTAG_Debugger_FactoryAIOT_Pro-if00-port0",
        "/dev/serial/by-id/usb-SIPEED_JTAG_Debugger_FactoryAIOT_Pro-if01-port0",
        "/dev/serial/by-id/usb-Ericsson_modem-if09",
    ]
    monkeypatch.setattr(capture_neorv32_uart.glob, "glob", lambda pattern: candidates if pattern == "/dev/serial/by-id/*" else [])
    monkeypatch.setattr(Path, "exists", lambda self: str(self) in candidates)
    monkeypatch.setattr(Path, "resolve", lambda self: self)
    monkeypatch.setattr(capture_neorv32_uart.os, "access", lambda path, mode: True)

    status = choose_serial()

    assert status["ready"] is True
    assert status["path"].endswith("if01-port0")
    assert status["source"] == "auto"


def test_board_firmware_target_uses_toolchain_probe_and_absolute_resolved_home() -> None:
    makefile = (REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile").read_text(encoding="utf-8")

    assert "tools/check_neorv32_toolchain.py" in makefile
    assert "NEORV32_FW_PROFILE ?= auto" in makefile
    assert "TOOLCHAIN_ARGS" in makefile
    assert "$$TOOLCHAIN_ARGS USE_CFS_AXIS_MMIO=1" in makefile


def test_neorv32_benchmark_makefile_uses_user_flags_not_unused_app_cflags() -> None:
    makefile = (REPO_ROOT / "firmware" / "neorv32_ascon_benchmark" / "Makefile").read_text(encoding="utf-8")

    assert "APP_CFLAGS" not in makefile
    assert "USER_FLAGS += -DASCON_BENCH_USE_AXIS_MMIO=1" in makefile
    assert "USER_FLAGS += -DASCON_ACCEL_AXIS_MMIO_BASE_ADDR=$(AXIS_MMIO_BASE_ADDR)" in makefile
    assert "NEORV32_ROM_SIZE ?= 32k" in makefile




def test_neorv32_benchmark_has_freestanding_runtime_for_no_libc_build() -> None:
    runtime = (REPO_ROOT / "firmware" / "neorv32_ascon_benchmark" / "freestanding_runtime.c").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "firmware" / "neorv32_ascon_benchmark" / "Makefile").read_text(encoding="utf-8")

    assert "void *memset" in runtime
    assert "void *memcpy" in runtime
    assert "int memcmp" in runtime
    assert "APP_SRC += freestanding_runtime.c" in makefile
    assert "-nostdlib" in makefile
    assert "ASCON_BENCH_FREESTANDING" in makefile
    assert "__udivsi3" in runtime
    assert "__ashldi3" in runtime
    assert "unsigned char _ctype_" in runtime

def test_toolchain_probe_cli_reports_without_traceback() -> None:
    completed = subprocess.run(
        [sys.executable, "tools/check_neorv32_toolchain.py", "--prefix", "definitely-missing-riscv-prefix-", "--check"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "compiler" in completed.stdout or "not found" in completed.stdout


def test_toolchain_probe_does_not_use_invalid_no_entry_linker_flag() -> None:
    text = (REPO_ROOT / "tools" / "check_neorv32_toolchain.py").read_text(encoding="utf-8")

    assert "--no-entry" not in text
    assert "-Wl,-e,main" in text
    assert "-Wl,-e,_start" in text


def test_flake_creates_readelf_compatibility_wrapper_without_gcc_gate() -> None:
    text = (REPO_ROOT / "flake.nix").read_text(encoding="utf-8")
    assert "readelf" in text
    assert "per-tool" in text
    assert "! command -v riscv-none-elf-$tool" in text
    assert "! command -v riscv-none-elf-gcc" not in text


def test_toolchain_probe_requires_neorv32_image_generation_tools() -> None:
    text = (REPO_ROOT / "tools" / "check_neorv32_toolchain.py").read_text(encoding="utf-8")
    assert "REQUIRED_TOOLS" in text
    assert "readelf" in text
    assert "objcopy" in text
    assert "missing required RISC-V toolchain programs" in text


def test_soft_toolchain_helper_is_project_local_and_prints_prefix() -> None:
    text = (REPO_ROOT / "tools" / "ensure_neorv32_soft_toolchain.py").read_text(encoding="utf-8")

    assert "external" in text
    assert "riscv32-unknown-elf.gcc-13.2.0.tar.gz" in text
    assert "$HOME" not in text
    assert "--print-prefix" in text
    assert "rv32i-131023" in text


def test_board_makefile_has_board_safe_soft_firmware_target() -> None:
    makefile = (REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile").read_text(encoding="utf-8")

    assert "firmware-soft:" in makefile
    assert "--profile freestanding-soft --check" in makefile
    assert "MARCH=rv32i_zicsr_zifencei" in makefile
    assert "MABI=ilp32" in makefile
    assert "FREESTANDING=1" in makefile
    assert "LD_LIBS=" in makefile


def test_soft_toolchain_doc_warns_hardfloat_is_not_release_profile() -> None:
    doc = (REPO_ROOT / "docs" / "neorv32_soft_toolchain.md").read_text(encoding="utf-8")

    assert "RV32I" in doc
    assert "ILP32" in doc
    assert "hardfloat-nix" in doc
    assert "smoke test only" in doc
    assert "freestanding" in doc.lower()
    assert "does not depend on `steam-run`" in doc


def test_soft_toolchain_helper_reports_nixos_stub_ld_without_unfree_wrapper() -> None:
    text = (REPO_ROOT / "tools" / "ensure_neorv32_soft_toolchain.py").read_text(encoding="utf-8")

    assert "NixOS cannot run dynamically linked executables" in text
    assert "nix-ld/FHS compatibility" in text
    assert "steam-run" not in text
    assert "nixos-wrapped-bin" not in text


def test_flake_does_not_pull_unfree_steam_run_for_prebuilt_toolchain() -> None:
    text = (REPO_ROOT / "flake.nix").read_text(encoding="utf-8")

    assert "steam-run" not in text


def test_soft_firmware_target_uses_nix_native_freestanding_profile_without_unfree_wrapper() -> None:
    makefile = (REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile").read_text(encoding="utf-8")

    assert "firmware-soft:" in makefile
    assert "--profile freestanding-soft --check" in makefile
    assert "--wrap-nixos" not in makefile
