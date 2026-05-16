#!/usr/bin/env python3
"""Create a dry-run build plan for the Tang Nano 9K NEORV32 stream-ASCON target."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from prepare_neorv32_stream_board_build import DEFAULT_OUT as DEFAULT_PACKAGE_DIR, prepare_package, validate_package

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_OUT = REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "build_plan.json"
DEFAULT_MD_OUT = REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "build_plan.md"


class BoardBuildPlanError(RuntimeError):
    """Raised when the dry-run board build plan cannot be produced."""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tool_status(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"available": path is not None, "path": path}


def _existing_sources(package_dir: Path, rel_list: list[str]) -> tuple[list[str], list[str]]:
    existing: list[str] = []
    missing: list[str] = []
    for relpath in rel_list:
        if (REPO_ROOT / relpath).exists():
            existing.append(relpath)
        else:
            missing.append(relpath)
    return existing, missing


def build_board_plan(package_dir: Path = DEFAULT_PACKAGE_DIR, *, ensure_package: bool = False) -> dict[str, Any]:
    """Build a deterministic dry-run plan from the generated board package."""
    if ensure_package and not (package_dir / "package.json").exists():
        prepare_package(package_dir, clean=True)
    validate_package(package_dir)

    package = _read_json(package_dir / "package.json")
    manifest = _read_json(package_dir / "manifest.json")
    preflight = _read_json(package_dir / "preflight.json")
    memory_map = _read_json(package_dir / "memory_map.json")

    all_sources = (package_dir / "rtl_sources_all.f").read_text(encoding="utf-8").splitlines()
    verilog_sources = (package_dir / "rtl_sources_verilog.f").read_text(encoding="utf-8").splitlines()
    vhdl_sources = (package_dir / "rtl_sources_vhdl.f").read_text(encoding="utf-8").splitlines()
    existing, missing = _existing_sources(package_dir, all_sources)

    firmware_header = package_dir / "firmware" / "ascon_stream_axis_mmio_config.h"
    firmware_mk = package_dir / "firmware" / "neorv32_stream_defines.mk"
    commands = package_dir / "commands.sh"

    required_checks = {
        "package_metadata_exists": (package_dir / "package.json").exists(),
        "manifest_exists": (package_dir / "manifest.json").exists(),
        "preflight_exists": (package_dir / "preflight.json").exists(),
        "memory_map_matches_manifest": memory_map["csr_base"] == manifest["memory_map"]["csr_window"]["base"]
        and memory_map["axis_mmio_base"] == manifest["memory_map"]["axis_mmio_window"]["base"],
        "cfs_wrapper_present": manifest["top"]["cfs_wrapper"] in all_sources,
        "accelerator_system_present": manifest["top"]["accelerator_system"] in all_sources,
        "mixed_language_split_present": bool(verilog_sources) and bool(vhdl_sources),
        "all_sources_exist": not missing,
        "firmware_header_exists": firmware_header.exists(),
        "firmware_make_fragment_exists": firmware_mk.exists(),
        "commands_script_exists": commands.exists(),
        "stream_mode_selected": package["firmware"]["make_mode"] == "USE_CFS_AXIS_MMIO=1",
    }

    optional_tools = {
        name: _tool_status(name)
        for name in [
            "python",
            "pytest",
            "iverilog",
            "vvp",
            "yosys",
            "yowasp-yosys",
            "nextpnr-himbaechel",
            "yowasp-nextpnr-himbaechel-gowin",
            "gowin_pack",
            "openFPGALoader",
        ]
    }

    plan = {
        "schema_version": 1,
        "name": "tangnano9k_neorv32_stream_axis_mmio_build_plan",
        "package_dir": str(package_dir),
        "board": manifest["board"],
        "memory_map": memory_map,
        "firmware": {
            "directory": package["firmware"]["directory"],
            "mode": package["firmware"]["make_mode"],
            "command": package["firmware"]["command"],
            "defines": package["firmware"]["defines"],
            "generated_header": "firmware/ascon_stream_axis_mmio_config.h",
            "generated_make_fragment": "firmware/neorv32_stream_defines.mk",
        },
        "rtl": {
            "source_count": len(all_sources),
            "verilog_count": len(verilog_sources),
            "vhdl_count": len(vhdl_sources),
            "sources": all_sources,
            "verilog_sources": verilog_sources,
            "vhdl_sources": vhdl_sources,
            "existing_sources": existing,
            "missing_sources": missing,
            "cfs_wrapper": manifest["top"]["cfs_wrapper"],
            "accelerator_system": manifest["top"]["accelerator_system"],
        },
        "checks": required_checks,
        "optional_tools": optional_tools,
        "dry_run_ok": all(required_checks.values()),
        "stages": [
            {
                "name": "pre_board_validation",
                "commands": [
                    "make neorv32-stream-board-manifest",
                    "make neorv32-stream-board-preflight",
                    "make neorv32-stream-board-package",
                    "make stream-axis-mmio-system-sim",
                ],
            },
            {
                "name": "firmware_build",
                "commands": [package["firmware"]["command"]],
            },
            {
                "name": "rtl_integration",
                "commands": [
                    "Compile rtl_sources_verilog.f as design Verilog sources.",
                    "Compile rtl_sources_vhdl.f with the NEORV32 library as the CFS implementation.",
                    "Use neorv32_cfs_ascon_stream_axis_mmio.vhd in place of the stock NEORV32 CFS template.",
                ],
            },
            {
                "name": "gowin_board_build",
                "commands": [
                    "Run the Tang Nano 9K NEORV32 synthesis/place/pack flow with the generated CFS wrapper.",
                    "Program with openFPGALoader once the bitstream is produced.",
                ],
            },
            {
                "name": "uart_report",
                "commands": [
                    "Capture UART output to a log file.",
                    "make neorv32-stream-uart-report LOG=/path/to/uart.log",
                ],
            },
        ],
        "notes": [
            "This is a dry-run plan: it validates the package and records tool availability, but does not synthesize or program hardware.",
            "Missing optional FPGA tools are reported, not treated as plan failures.",
        ],
    }
    if not plan["dry_run_ok"]:
        failed = [name for name, ok in required_checks.items() if not ok]
        raise BoardBuildPlanError("board build dry-run checks failed: " + ", ".join(failed))
    return plan


def render_markdown(plan: dict[str, Any]) -> str:
    """Render the dry-run board build plan as Markdown."""
    lines = [
        "# NEORV32 stream board dry-run build plan",
        "",
        f"Package: `{plan['package_dir']}`",
        f"Board: {plan['board']['name']} ({plan['board']['fpga_family']})",
        f"Dry-run status: {'ok' if plan['dry_run_ok'] else 'failed'}",
        "",
        "## Memory map",
        "",
        f"- CSR/MMIO base: `{plan['memory_map']['csr_base']}`",
        f"- AXI-stream MMIO base: `{plan['memory_map']['axis_mmio_base']}`",
        "",
        "## RTL",
        "",
        f"- Sources: {plan['rtl']['source_count']}",
        f"- Verilog: {plan['rtl']['verilog_count']}",
        f"- VHDL: {plan['rtl']['vhdl_count']}",
        f"- CFS wrapper: `{plan['rtl']['cfs_wrapper']}`",
        "",
        "## Firmware",
        "",
        f"- Directory: `{plan['firmware']['directory']}`",
        f"- Mode: `{plan['firmware']['mode']}`",
        f"- Command: `{plan['firmware']['command']}`",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for key, value in plan["checks"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Optional tools", "", "| Tool | Available | Path |", "|---|---:|---|"])
    for name, status in plan["optional_tools"].items():
        lines.append(f"| `{name}` | {status['available']} | {status['path'] or 'n/a'} |")
    lines.extend(["", "## Stages", ""])
    for stage in plan["stages"]:
        lines.append(f"### {stage['name']}")
        lines.append("")
        for command in stage["commands"]:
            lines.append(f"- `{command}`")
        lines.append("")
    return "\n".join(lines)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", dest="package_dir", type=Path, default=DEFAULT_PACKAGE_DIR, help="generated board package directory")
    parser.add_argument("--ensure-package", action="store_true", help="generate the package first if it is missing")
    parser.add_argument("--json", action="store_true", help="print or write JSON")
    parser.add_argument("--markdown", action="store_true", help="print or write Markdown")
    parser.add_argument("--out", type=Path, default=None, help="write the selected report to this path")
    parser.add_argument("--write-defaults", action="store_true", help="write build_plan.json and build_plan.md under build/neorv32_stream_axis_mmio")
    parser.add_argument("--check", action="store_true", help="validate the package/plan and print ok")
    args = parser.parse_args()

    plan = build_board_plan(args.package_dir, ensure_package=args.ensure_package)

    if args.write_defaults:
        _write(DEFAULT_JSON_OUT, json.dumps(plan, indent=2, sort_keys=True) + "\n")
        _write(DEFAULT_MD_OUT, render_markdown(plan))

    if args.check:
        print("ok")
        return 0

    if args.markdown:
        rendered = render_markdown(plan)
    else:
        rendered = json.dumps(plan, indent=2, sort_keys=True) + "\n"

    if args.out:
        _write(args.out, rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
