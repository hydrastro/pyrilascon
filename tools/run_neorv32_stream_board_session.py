#!/usr/bin/env python3
"""Prepare or summarize a Tang Nano 9K NEORV32 stream-ASCON board session.

This tool is intentionally safe by default: it validates the generated board
package, records the expected programming/UART/report steps, and can optionally
parse a captured UART benchmark log. Hardware programming is only attempted when
``--program`` is used without ``--dry-run``.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from parse_neorv32_ascon_uart_log import UartBenchmarkParseError, parse_uart_log, render_markdown as render_uart_markdown
from plan_neorv32_stream_board_build import DEFAULT_PACKAGE_DIR, build_board_plan
from prepare_neorv32_stream_board_build import prepare_package

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSION_DIR = REPO_ROOT / "build" / "neorv32_stream_axis_mmio" / "session"
DEFAULT_JSON_OUT = DEFAULT_SESSION_DIR / "session.json"
DEFAULT_MD_OUT = DEFAULT_SESSION_DIR / "session.md"


class BoardSessionError(RuntimeError):
    """Raised when a board session cannot be prepared or summarized."""


def _tool_status(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"available": path is not None, "path": path}


def _read_uart_report(path: Path, *, strict: bool) -> dict[str, Any]:
    if not path.exists():
        raise BoardSessionError(f"UART log file does not exist: {path}")
    if not path.is_file():
        raise BoardSessionError(f"UART log path is not a file: {path}")
    try:
        return parse_uart_log(path.read_text(encoding="utf-8"), strict=strict)
    except UartBenchmarkParseError as exc:
        raise BoardSessionError(f"UART report failed: {exc}") from exc


def _program_command(bitstream: Path | None) -> list[str] | None:
    if bitstream is None:
        return None
    return ["openFPGALoader", "-b", "tangnano9k", str(bitstream)]


def _run_programming(bitstream: Path, *, dry_run: bool) -> dict[str, Any]:
    loader = _tool_status("openFPGALoader")
    command = _program_command(bitstream)
    result: dict[str, Any] = {
        "requested": True,
        "dry_run": dry_run,
        "tool": loader,
        "command": command,
        "returncode": None,
        "stdout": "",
        "stderr": "",
    }
    if not bitstream.exists():
        raise BoardSessionError(f"bitstream file does not exist: {bitstream}")
    if not bitstream.is_file():
        raise BoardSessionError(f"bitstream path is not a file: {bitstream}")
    if not loader["available"]:
        raise BoardSessionError("openFPGALoader is not available on PATH")
    if dry_run:
        return result

    completed = subprocess.run(command, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    result.update(
        {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    )
    if completed.returncode != 0:
        raise BoardSessionError(f"openFPGALoader failed with return code {completed.returncode}")
    return result


def build_session_report(
    *,
    package_dir: Path = DEFAULT_PACKAGE_DIR,
    ensure_package: bool = False,
    bitstream: Path | None = None,
    uart_log: Path | None = None,
    strict_uart: bool = False,
    program: bool = False,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Build a deterministic board-session report.

    The report is useful before hardware exists, during hardware bring-up, and
    after a UART log has been captured from a programmed board.
    """
    if ensure_package and not (package_dir / "package.json").exists():
        prepare_package(package_dir, clean=True)

    plan = build_board_plan(package_dir, ensure_package=ensure_package)
    openfpgaloader = _tool_status("openFPGALoader")
    bitstream_info = {
        "path": None if bitstream is None else str(bitstream),
        "present": None if bitstream is None else bitstream.exists() and bitstream.is_file(),
        "program_command": _program_command(bitstream),
    }

    programming = {
        "requested": program,
        "dry_run": dry_run,
        "tool": openfpgaloader,
        "command": _program_command(bitstream),
        "returncode": None,
        "stdout": "",
        "stderr": "",
    }
    if program:
        if bitstream is None:
            raise BoardSessionError("--program requires --bitstream")
        programming = _run_programming(bitstream, dry_run=dry_run)

    uart_report: dict[str, Any] | None = None
    if uart_log is not None:
        uart_report = _read_uart_report(uart_log, strict=strict_uart)

    checks = {
        "package_plan_ok": plan["dry_run_ok"],
        "bitstream_present_if_requested": True if bitstream is None else bitstream.exists() and bitstream.is_file(),
        "programming_tool_available_if_requested": True if not program else openfpgaloader["available"],
        "uart_log_present_if_requested": True if uart_log is None else uart_log.exists() and uart_log.is_file(),
        "uart_report_passed_if_supplied": True if uart_report is None else uart_report["headline"] == "pass",
    }

    report = {
        "schema_version": 1,
        "name": "tangnano9k_neorv32_stream_axis_mmio_board_session",
        "package_dir": str(package_dir),
        "memory_map": plan["memory_map"],
        "firmware": plan["firmware"],
        "rtl": {
            "source_count": plan["rtl"]["source_count"],
            "cfs_wrapper": plan["rtl"]["cfs_wrapper"],
            "accelerator_system": plan["rtl"]["accelerator_system"],
        },
        "tools": {
            "openFPGALoader": openfpgaloader,
        },
        "bitstream": bitstream_info,
        "programming": programming,
        "uart_log": {
            "path": None if uart_log is None else str(uart_log),
            "present": None if uart_log is None else uart_log.exists() and uart_log.is_file(),
            "strict": strict_uart,
        },
        "uart_report": uart_report,
        "checks": checks,
        "session_ok": all(checks.values()),
        "next_actions": [
            "Run make neorv32-stream-board-package and make neorv32-stream-board-build-plan before synthesis.",
            "Build the NEORV32 firmware with USE_CFS_AXIS_MMIO=1.",
            "Integrate rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd as the CFS implementation.",
            "Synthesize/place/pack the Tang Nano 9K design and program the bitstream.",
            "Capture UART output and run make neorv32-stream-uart-report LOG=/path/to/uart.log.",
        ],
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    """Render a board-session report as Markdown."""
    bitstream = report["bitstream"]
    programming = report["programming"]
    uart_report = report.get("uart_report")
    lines = [
        "# NEORV32 stream board session",
        "",
        f"Session status: {'ok' if report['session_ok'] else 'needs attention'}",
        f"Package: `{report['package_dir']}`",
        "",
        "## Memory map",
        "",
        f"- CSR/MMIO base: `{report['memory_map']['csr_base']}`",
        f"- AXI-stream MMIO base: `{report['memory_map']['axis_mmio_base']}`",
        "",
        "## Firmware",
        "",
        f"- Mode: `{report['firmware']['mode']}`",
        f"- Command: `{report['firmware']['command']}`",
        "",
        "## Bitstream/programming",
        "",
        f"- Bitstream: `{bitstream['path'] or 'not provided'}`",
        f"- Bitstream present: {bitstream['present']}",
        f"- openFPGALoader available: {report['tools']['openFPGALoader']['available']}",
        f"- Program requested: {programming['requested']}",
        f"- Dry-run: {programming['dry_run']}",
    ]
    if programming.get("command"):
        lines.append(f"- Program command: `{' '.join(programming['command'])}`")

    lines.extend(["", "## Checks", "", "| Check | Result |", "|---|---:|"])
    for key, value in report["checks"].items():
        lines.append(f"| `{key}` | {value} |")

    if uart_report is not None:
        lines.extend(["", "## UART benchmark", ""])
        lines.append(render_uart_markdown(uart_report).strip())

    lines.extend(["", "## Next actions", ""])
    for action in report["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", dest="package_dir", type=Path, default=DEFAULT_PACKAGE_DIR, help="generated board package directory")
    parser.add_argument("--ensure-package", action="store_true", help="generate the package first if needed")
    parser.add_argument("--bitstream", type=Path, default=None, help="bitstream to program or record in the session report")
    parser.add_argument("--program", action="store_true", help="program the bitstream with openFPGALoader")
    parser.add_argument("--dry-run", action="store_true", default=True, help="do not program hardware; record the command only")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="allow hardware programming when --program is set")
    parser.add_argument("--uart-log", type=Path, default=None, help="captured UART benchmark log to parse")
    parser.add_argument("--strict-uart", action="store_true", help="require the UART benchmark report to pass strict checks")
    parser.add_argument("--json", action="store_true", help="print or write JSON")
    parser.add_argument("--markdown", action="store_true", help="print or write Markdown")
    parser.add_argument("--out", type=Path, default=None, help="write the selected report to this path")
    parser.add_argument("--write-defaults", action="store_true", help="write session.json and session.md under build/neorv32_stream_axis_mmio/session")
    parser.add_argument("--check", action="store_true", help="validate the session inputs and print ok")
    args = parser.parse_args()

    try:
        report = build_session_report(
            package_dir=args.package_dir,
            ensure_package=args.ensure_package,
            bitstream=args.bitstream,
            uart_log=args.uart_log,
            strict_uart=args.strict_uart,
            program=args.program,
            dry_run=args.dry_run,
        )
    except BoardSessionError as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        return 2

    if args.write_defaults:
        _write(DEFAULT_JSON_OUT, json.dumps(report, indent=2, sort_keys=True) + "\n")
        _write(DEFAULT_MD_OUT, render_markdown(report))

    if args.check:
        print("ok")
        return 0

    rendered = render_markdown(report) if args.markdown else json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        _write(args.out, rendered)
    elif args.json or args.markdown or not args.write_defaults:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
