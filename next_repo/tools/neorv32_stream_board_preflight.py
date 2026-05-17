#!/usr/bin/env python3
"""Generate and validate the Tang Nano 9K NEORV32 stream ASCON board preflight plan."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from ensure_neorv32_checkout import DEFAULT_VENDOR_DIR, locate_neorv32
from print_neorv32_stream_board_manifest import DEFAULT_MANIFEST, load_manifest, render_text, validate_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "preflight.json"
ROOT_MAKEFILE = REPO_ROOT / "Makefile"
BOARD_DIR = REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio"
BOARD_MAKEFILE = BOARD_DIR / "Makefile"


class PreflightError(RuntimeError):
    """Raised when the board preflight checks fail."""


def _read_file_list(relpath: str) -> list[str]:
    file_list = REPO_ROOT / relpath
    return [
        line.strip()
        for line in file_list.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _tool_status(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"name": name, "available": path is not None, "path": path}


def _neorv32_status(path: Path | None) -> dict[str, Any]:
    located = locate_neorv32(explicit=path, vendor_dir=DEFAULT_VENDOR_DIR)
    home = Path(located["home"]) if located["home"] else None
    return {
        "provided": path is not None or any(item["source"] == "env:NEORV32_HOME" for item in located["candidates"]),
        "path": str(home) if home else None,
        "source": located["source"],
        "project_local_default": str(DEFAULT_VENDOR_DIR),
        "exists": home.exists() if home else False,
        "common_mk": (home / "sw" / "common" / "common.mk").exists() if home else False,
        "ready_for_firmware_build": bool(located["ready"]),
    }


def _makefile_has_target(makefile: Path, target: str) -> bool:
    text = makefile.read_text(encoding="utf-8")
    return f"{target}:" in text


def build_preflight_plan(manifest: dict[str, Any], neorv32_home: Path | None) -> dict[str, Any]:
    validate_manifest(manifest)
    memory = manifest["memory_map"]
    firmware = manifest["firmware"]
    rtl = manifest["rtl"]
    # Board-specific orchestration intentionally lives in the board directory.
    # The root Makefile is kept generic for model/RTL/test/report targets.
    root_targets = {
        "stream-axis-mmio-system-sim": _makefile_has_target(ROOT_MAKEFILE, "stream-axis-mmio-system-sim"),
    }
    board_targets = {
        "all": _makefile_has_target(BOARD_MAKEFILE, "all"),
        "clean": _makefile_has_target(BOARD_MAKEFILE, "clean"),
        "tools": _makefile_has_target(BOARD_MAKEFILE, "tools"),
        "prog-sram": _makefile_has_target(BOARD_MAKEFILE, "prog-sram"),
        "manifest": _makefile_has_target(BOARD_MAKEFILE, "manifest"),
        "check": _makefile_has_target(BOARD_MAKEFILE, "check"),
        "preflight": _makefile_has_target(BOARD_MAKEFILE, "preflight"),
        "firmware": _makefile_has_target(BOARD_MAKEFILE, "firmware"),
        "firmware-soft": _makefile_has_target(BOARD_MAKEFILE, "firmware-soft"),
        "rtl-list": _makefile_has_target(BOARD_MAKEFILE, "rtl-list"),
        "memory-map": _makefile_has_target(BOARD_MAKEFILE, "memory-map"),
    }
    return {
        "schema_version": 1,
        "name": "tangnano9k_neorv32_stream_axis_mmio_preflight",
        "manifest": manifest["name"],
        "board": manifest["board"],
        "memory_map": {
            "ascon_cfs_base": memory["ascon_cfs_base"],
            "csr_base": memory["csr_window"]["base"],
            "axis_mmio_base": memory["axis_mmio_window"]["base"],
            "axis_mmio_offset": memory["axis_mmio_window"]["offset"],
        },
        "firmware": {
            "directory": firmware["directory"],
            "make_mode": firmware["make_mode"],
            "command": firmware["command"],
            "defines": firmware["defines"],
        },
        "rtl": {
            "primary_file_list": rtl["primary_file_list"],
            "sources": _read_file_list(rtl["primary_file_list"]),
            "cfs_wrapper": manifest["top"]["cfs_wrapper"],
            "accelerator_system": manifest["top"]["accelerator_system"],
        },
        "targets": {
            "root_makefile": root_targets,
            "board_makefile": board_targets,
        },
        "host_tools": {
            name: _tool_status(name)
            for name in ["python", "pytest", "iverilog", "vvp", "yosys", "nextpnr-himbaechel", "gowin_pack", "openFPGALoader"]
        },
        "neorv32_home": _neorv32_status(neorv32_home),
        "pre_board_commands": [
            "make -C boards/tangnano9k/neorv32_stream_axis_mmio manifest",
            "make -C boards/tangnano9k/neorv32_stream_axis_mmio preflight",
            "python -m pytest -q tests/test_neorv32_stream_cfs_integration.py",
            "python -m pytest -q tests/test_stream_axis_mmio_system_sim.py",
            "make stream-axis-mmio-system-sim",
        ],
        "bringup_commands": [
            "make -C boards/tangnano9k/neorv32_stream_axis_mmio clean",
            "make -C boards/tangnano9k/neorv32_stream_axis_mmio tools",
            "make -C boards/tangnano9k/neorv32_stream_axis_mmio",
            "integrate rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd as neorv32_cfs",
            "synthesize/program the NEORV32 Tang Nano 9K SoC image",
            "capture UART benchmark output and compare software/hardware cycles",
        ],
    }


def validate_preflight_plan(plan: dict[str, Any], require_neorv32_home: bool = False) -> None:
    missing_root = [name for name, ok in plan["targets"]["root_makefile"].items() if not ok]
    missing_board = [name for name, ok in plan["targets"]["board_makefile"].items() if not ok]
    if missing_root:
        raise PreflightError(f"root Makefile is missing generic targets: {', '.join(missing_root)}")
    if missing_board:
        raise PreflightError(f"board Makefile is missing targets: {', '.join(missing_board)}")
    if require_neorv32_home and not plan["neorv32_home"]["ready_for_firmware_build"]:
        raise PreflightError("NEORV32_HOME is missing or does not contain sw/common/common.mk")
    sources = plan["rtl"]["sources"]
    missing_sources = [source for source in sources if not (REPO_ROOT / source).exists()]
    if missing_sources:
        raise PreflightError(f"RTL file list contains missing sources: {', '.join(missing_sources)}")


def render_preflight_text(plan: dict[str, Any]) -> str:
    memory = plan["memory_map"]
    neorv32 = plan["neorv32_home"]
    lines = [
        f"name: {plan['name']}",
        f"manifest: {plan['manifest']}",
        f"board: {plan['board']['name']} ({plan['board']['fpga_family']})",
        "",
        "memory map:",
        f"  CSR       {memory['csr_base']}",
        f"  AXI-MMIO  {memory['axis_mmio_base']} offset={memory['axis_mmio_offset']}",
        "",
        "firmware:",
        f"  directory: {plan['firmware']['directory']}",
        f"  mode:      {plan['firmware']['make_mode']}",
        f"  command:   {plan['firmware']['command']}",
        "",
        "rtl:",
        f"  file list: {plan['rtl']['primary_file_list']}",
        f"  sources:   {len(plan['rtl']['sources'])}",
        "",
        "NEORV32_HOME:",
        f"  provided: {neorv32['provided']}",
        f"  ready:    {neorv32['ready_for_firmware_build']}",
        "",
        "pre-board commands:",
        *[f"  {cmd}" for cmd in plan["pre_board_commands"]],
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--neorv32-home", type=Path, default=None, help="optional NEORV32 checkout path; defaults to NEORV32_HOME")
    parser.add_argument("--out", type=Path, default=None, help="write preflight JSON to this path")
    parser.add_argument("--json", action="store_true", help="print preflight JSON")
    parser.add_argument("--check", action="store_true", help="validate and print ok")
    parser.add_argument("--require-neorv32-home", action="store_true", help="fail unless NEORV32_HOME is build-ready")
    args = parser.parse_args()

    neorv32_home = args.neorv32_home

    try:
        manifest = load_manifest(args.manifest)
        plan = build_preflight_plan(manifest, neorv32_home)
        validate_preflight_plan(plan, require_neorv32_home=args.require_neorv32_home)
    except PreflightError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.check:
        print("ok")
    elif args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(render_preflight_text(plan))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
