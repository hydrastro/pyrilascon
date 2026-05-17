#!/usr/bin/env python3
"""Diagnose local prerequisites for Tang Nano 9K NEORV32 stream-ASCON bring-up.

The doctor intentionally does not build firmware, program hardware, or open the
serial port.  It checks the common host-side blockers before the first board
attempt: a real NEORV32 checkout, generated handoff/package files, UART tool
availability, serial-device permissions, and openFPGALoader availability.
"""
from __future__ import annotations

import argparse
import grp
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

from capture_neorv32_uart import choose_serial, serial_candidates
from ensure_neorv32_checkout import DEFAULT_VENDOR_DIR, locate_neorv32
from check_neorv32_toolchain import build_report as build_toolchain_report

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "package"
DEFAULT_HANDOFF = REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "gowin_handoff"
DEFAULT_REPORT_JSON = REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "bringup_doctor.json"
DEFAULT_REPORT_MD = REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "bringup_doctor.md"
PLACEHOLDER_NEORV32_HOME = "/path/to/neorv32"


class BringupDoctorError(RuntimeError):
    """Raised when the doctor cannot inspect the requested environment."""


def _tool_status(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"available": path is not None, "path": path}


def _riscv_toolchain_status() -> dict[str, Any]:
    canonical = _tool_status("riscv-none-elf-gcc")
    nixpkgs_prefix = _tool_status("riscv32-none-elf-gcc")
    try:
        probe = build_toolchain_report(prefix="riscv-none-elf-", requested_profile="auto")
        probe_dict = {
            "selected_profile": probe.selected_profile,
            "selected_march": probe.selected_march,
            "selected_mabi": probe.selected_mabi,
            "soft_ok": probe.soft.ok,
            "hardfloat_ok": probe.hardfloat.ok,
            "warnings": probe.warnings,
            "errors": probe.errors,
        }
        ready = probe.selected_profile is not None
        message = (
            f"RISC-V GCC usable with profile {probe.selected_profile}."
            if ready
            else "RISC-V GCC was found but cannot link the NEORV32 firmware profiles; install a multilib riscv-none-elf toolchain."
        )
    except Exception as exc:  # pragma: no cover - defensive for host-specific toolchains
        probe_dict = {"error": str(exc)}
        ready = canonical["available"] or nixpkgs_prefix["available"]
        message = (
            "RISC-V GCC toolchain found, but ABI probing failed."
            if ready
            else "RISC-V GCC toolchain missing; enter `nix develop` or install a riscv-none-elf toolchain."
        )
    return {
        "ready": ready,
        "canonical": canonical,
        "nixpkgs_prefix": nixpkgs_prefix,
        "probe": probe_dict,
        "message": message,
    }


def _path_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
    }


def _neorv32_status(neorv32_home: Path | None) -> dict[str, Any]:
    located = locate_neorv32(explicit=neorv32_home, vendor_dir=DEFAULT_VENDOR_DIR)
    ready = bool(located["ready"])
    path = located["home"]
    candidates = located["candidates"]
    selected = next((item for item in candidates if item.get("ready")), None)
    provided = neorv32_home is not None or bool(os.environ.get("NEORV32_HOME"))
    is_placeholder = any(item.get("is_placeholder") for item in candidates[:2])

    if ready:
        message = f"NEORV32 checkout found via {located['source']}."
    elif is_placeholder:
        message = "NEORV32_HOME still uses the documentation placeholder; replace it or run `make -C boards/tangnano9k/neorv32_stream_axis_mmio deps`."
    else:
        message = "No usable NEORV32 checkout found; set NEORV32_HOME or run `make -C boards/tangnano9k/neorv32_stream_axis_mmio deps`."

    return {
        "provided": provided,
        "path": path if path is not None else (str(neorv32_home) if neorv32_home else None),
        "source": located["source"],
        "project_local_default": str(DEFAULT_VENDOR_DIR),
        "is_placeholder": is_placeholder,
        "exists": Path(path).exists() if path else False,
        "sw_dir": (Path(path) / "sw").exists() if path else False,
        "common_mk": (Path(path) / "sw" / "common" / "common.mk").exists() if path else False,
        "ready": ready,
        "candidates": candidates,
        "message": message,
    }


def _serial_status(device: Path | None) -> dict[str, Any]:
    chosen = choose_serial(device)
    path_value = chosen.get("path")
    path = Path(path_value) if path_value else None
    group = None
    mode = chosen.get("mode")
    if path is not None and path.exists():
        st = path.stat()
        try:
            group = grp.getgrgid(st.st_gid).gr_name
        except KeyError:
            group = str(st.st_gid)
        mode = stat.filemode(st.st_mode)

    return {
        "provided": device is not None or bool(os.environ.get("SERIAL")),
        "path": path_value,
        "source": chosen.get("source"),
        "exists": chosen.get("exists", False),
        "readable": chosen.get("readable", False),
        "writable": chosen.get("writable", False),
        "group": group,
        "mode": mode,
        "ready": chosen.get("ready", False),
        "candidates": chosen.get("candidates", [str(p) for p in serial_candidates()]),
        "message": chosen.get("message", "serial device status unavailable"),
    }


def build_report(
    *,
    neorv32_home: Path | None,
    serial_device: Path | None,
    package_dir: Path = DEFAULT_PACKAGE,
    handoff_dir: Path = DEFAULT_HANDOFF,
) -> dict[str, Any]:
    tools = {name: _tool_status(name) for name in ["picocom", "openFPGALoader", "python", "make"]}
    riscv_toolchain = _riscv_toolchain_status()
    neorv32 = _neorv32_status(neorv32_home)
    serial = _serial_status(serial_device)
    package = _path_status(package_dir)
    package["package_json"] = (package_dir / "package.json").exists()
    handoff = _path_status(handoff_dir)
    handoff["handoff_json"] = (handoff_dir / "handoff.json").exists()
    handoff["firmware_script"] = (handoff_dir / "scripts" / "02_build_firmware.sh").exists()
    handoff["uart_capture_script"] = (handoff_dir / "scripts" / "05_capture_uart.sh").exists()

    blockers: list[str] = []
    warnings: list[str] = []
    if not neorv32["ready"]:
        blockers.append(neorv32["message"])
    if not package["package_json"]:
        blockers.append("Board package is missing; run `make -C boards/tangnano9k/neorv32_stream_axis_mmio package`.")
    if not handoff["handoff_json"]:
        blockers.append("Gowin handoff is missing; run `make -C boards/tangnano9k/neorv32_stream_axis_mmio gowin-handoff`.")
    if not tools["picocom"]["available"]:
        warnings.append("picocom is not available; enter the dev shell or install it before UART capture.")
    if neorv32["ready"] and not riscv_toolchain["ready"]:
        blockers.append(riscv_toolchain["message"])
    if serial_device is not None and not serial["ready"]:
        blockers.append(serial["message"])
    elif serial_device is None:
        warnings.append(serial["message"])
    if not tools["openFPGALoader"]["available"]:
        warnings.append("openFPGALoader is not available; programming scripts will not work yet.")

    next_actions: list[str] = []
    if not neorv32["ready"]:
        next_actions.append("Set NEORV32_HOME to a real checkout or run `make -C boards/tangnano9k/neorv32_stream_axis_mmio deps` to clone into external/neorv32.")
    if serial_device is None:
        next_actions.append("Connect the board or set SERIAL explicitly; auto-detection checks /dev/serial/by-id, /dev/ttyUSB*, /dev/ttyACM*, and macOS /dev/cu.usb* devices.")
    elif not serial["ready"]:
        next_actions.append("Fix serial permissions, then start a new login shell or use `newgrp <device-group>`.")
    if neorv32["ready"] and riscv_toolchain["ready"]:
        next_actions.append("Build firmware with `make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware`.")
    elif neorv32["ready"] and not riscv_toolchain["ready"]:
        next_actions.append("Enter the updated `nix develop` shell or install a riscv-none-elf GCC toolchain before building firmware.")
    if serial["ready"]:
        next_actions.append(f"Capture UART with `make -C boards/tangnano9k/neorv32_stream_axis_mmio uart-capture SERIAL={serial_device} LOG=uart.log`.")
    next_actions.append("Parse a non-empty benchmark log with `make -C boards/tangnano9k/neorv32_stream_axis_mmio uart-report LOG=uart.log`.")

    return {
        "schema_version": 1,
        "name": "tangnano9k_neorv32_stream_bringup_doctor",
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "neorv32_home": neorv32,
        "serial_device": serial,
        "tools": tools,
        "riscv_toolchain": riscv_toolchain,
        "package": package,
        "handoff": handoff,
        "next_actions": next_actions,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"name: {report['name']}",
        f"ready: {report['ready']}",
        "",
        "NEORV32_HOME:",
        f"  path:  {report['neorv32_home']['path']}",
        f"  ready: {report['neorv32_home']['ready']}",
        f"  note:  {report['neorv32_home']['message']}",
        "",
        "serial:",
        f"  path:     {report['serial_device']['path']}",
        f"  ready:    {report['serial_device']['ready']}",
        f"  group:    {report['serial_device']['group']}",
        f"  mode:     {report['serial_device']['mode']}",
        f"  note:     {report['serial_device']['message']}",
        f"  candidates: {', '.join(report['serial_device'].get('candidates', [])) or 'none'}",
        "",
        "tools:",
        *[f"  {name}: {status['available']} {status['path'] or ''}" for name, status in report["tools"].items()],
        f"  riscv-none-elf-gcc: {report['riscv_toolchain']['canonical']['available']} {report['riscv_toolchain']['canonical']['path'] or ''}",
        f"  riscv32-none-elf-gcc: {report['riscv_toolchain']['nixpkgs_prefix']['available']} {report['riscv_toolchain']['nixpkgs_prefix']['path'] or ''}",
        f"  selected fw profile: {report['riscv_toolchain'].get('probe', {}).get('selected_profile')}",
        f"  selected march/mabi: {report['riscv_toolchain'].get('probe', {}).get('selected_march')}/{report['riscv_toolchain'].get('probe', {}).get('selected_mabi')}",
        "",
        "blockers:",
        *([f"  - {item}" for item in report["blockers"]] or ["  none"]),
        "",
        "warnings:",
        *([f"  - {item}" for item in report["warnings"]] or ["  none"]),
        "",
        "next actions:",
        *[f"  - {item}" for item in report["next_actions"]],
    ]
    return "\n".join(lines) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Tang Nano 9K NEORV32 stream-ASCON bring-up doctor",
        "",
        f"- Ready: `{report['ready']}`",
        "",
        "## Blockers",
        "",
        *([f"- {item}" for item in report["blockers"]] or ["- none"]),
        "",
        "## Warnings",
        "",
        *([f"- {item}" for item in report["warnings"]] or ["- none"]),
        "",
        "## Environment",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| NEORV32_HOME | {report['neorv32_home']['path']} |",
        f"| NEORV32 ready | {report['neorv32_home']['ready']} |",
        f"| NEORV32 project-local default | {report['neorv32_home'].get('project_local_default')} |",
        f"| Serial device | {report['serial_device']['path']} |",
        f"| Serial ready | {report['serial_device']['ready']} |",
        f"| Serial group | {report['serial_device']['group']} |",
        f"| Serial candidates | {', '.join(report['serial_device'].get('candidates', [])) or 'none'} |",
        f"| RISC-V GCC ready | {report['riscv_toolchain']['ready']} |",
        f"| riscv-none-elf-gcc | {report['riscv_toolchain']['canonical']['path']} |",
        f"| riscv32-none-elf-gcc | {report['riscv_toolchain']['nixpkgs_prefix']['path']} |",
        f"| Firmware profile | {report['riscv_toolchain'].get('probe', {}).get('selected_profile')} |",
        f"| Firmware MARCH/MABI | {report['riscv_toolchain'].get('probe', {}).get('selected_march')}/{report['riscv_toolchain'].get('probe', {}).get('selected_mabi')} |",
        "",
        "## Next actions",
        "",
        *[f"- {item}" for item in report["next_actions"]],
        "",
    ]
    return "\n".join(lines)


def _default_neorv32_home(cli_path: Path | None) -> Path | None:
    if cli_path is not None:
        return cli_path
    value = os.environ.get("NEORV32_HOME")
    return Path(value) if value else None


def _default_serial(cli_path: Path | None) -> Path | None:
    if cli_path is not None:
        return cli_path
    value = os.environ.get("SERIAL")
    return Path(value) if value else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neorv32-home", type=Path, default=None, help="NEORV32 checkout path; defaults to NEORV32_HOME")
    parser.add_argument("--serial-device", type=Path, default=None, help="UART device path; defaults to SERIAL")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--handoff-dir", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown", action="store_true", help="print Markdown report")
    parser.add_argument("--out", type=Path, help="write report to path instead of stdout")
    parser.add_argument("--write-defaults", action="store_true", help="write default JSON and Markdown reports")
    parser.add_argument("--check", action="store_true", help="return nonzero when blocking issues are found")
    args = parser.parse_args()

    report = build_report(
        neorv32_home=_default_neorv32_home(args.neorv32_home),
        serial_device=_default_serial(args.serial_device),
        package_dir=args.package_dir,
        handoff_dir=args.handoff_dir,
    )

    if args.write_defaults:
        DEFAULT_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        DEFAULT_REPORT_MD.write_text(render_markdown(report), encoding="utf-8")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        if args.markdown:
            args.out.write_text(render_markdown(report), encoding="utf-8")
        else:
            args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.markdown:
        print(render_markdown(report), end="")
    else:
        print(render_text(report), end="")

    if args.check and not report["ready"]:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
