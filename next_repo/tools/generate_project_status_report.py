#!/usr/bin/env python3
"""Generate an implementation/verification status report for the ASCON project.

The report is intentionally repo-local and deterministic: it checks for concrete
source, test, documentation, and board-handoff artifacts that represent each
milestone.  It does not claim that hardware has been programmed; board execution
must still be proven by a captured UART log and the UART report parser.
"""
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_OUT = REPO_ROOT / "build" / "project_status" / "project_status.json"
DEFAULT_MD_OUT = REPO_ROOT / "build" / "project_status" / "project_status.md"


@dataclass(frozen=True)
class Milestone:
    key: str
    title: str
    stage: str
    summary: str
    evidence: tuple[str, ...]
    limitations: tuple[str, ...] = ()


MILESTONES: tuple[Milestone, ...] = (
    Milestone(
        key="python_golden_model",
        title="Python golden model and KAT baseline",
        stage="model",
        summary="Typed Ascon model, KAT coverage, and generated permutation helpers are present.",
        evidence=(
            "ascon_hwmodel/aead.py",
            "ascon_hwmodel/aead_stream.py",
            "tests/test_known_answer_vectors.py",
            "tools/generate_verilog.py",
        ),
    ),
    Milestone(
        key="stream_contract_and_framer",
        title="AXI-stream contract and reusable framing layer",
        stage="rtl_streaming",
        summary="The stream contract and standalone framer specify the byte/keep/last/user rules.",
        evidence=(
            "docs/streaming_aead_contract.md",
            "rtl/stream/ascon_axis_framer.v",
            "tests/test_axis_framer.py",
        ),
    ),
    Milestone(
        key="stream_encrypt_backend",
        title="Stream-native AEAD128 encryption backend",
        stage="rtl_streaming",
        summary="Encryption consumes AD/text streams and emits ciphertext/tag without whole-message buffering.",
        evidence=(
            "rtl/stream/ascon_aead128_stream_encrypt.v",
            "tools/run_stream_encrypt_vector.py",
            "tests/test_aead128_stream_encrypt_sim.py",
            "docs/streaming_aead_simulation.md",
        ),
    ),
    Milestone(
        key="buffered_decrypt_backend",
        title="Buffered authenticated decrypt backend",
        stage="rtl_streaming",
        summary="Decrypt uses quarantine buffering and suppresses plaintext unless tag verification succeeds.",
        evidence=(
            "rtl/stream/ascon_aead128_stream_decrypt_buffered.v",
            "tools/run_stream_decrypt_vector.py",
            "tests/test_aead128_stream_decrypt_sim.py",
            "docs/streaming_aead_decrypt_buffered_backend.md",
        ),
        limitations=(
            "Buffered decrypt is bounded by the configured internal quarantine buffer.",
            "Large production decrypt should move to DMA quarantine or a larger external buffer.",
        ),
    ),
    Milestone(
        key="unified_stream_backend",
        title="Unified stream AEAD backend wrapper",
        stage="rtl_integration",
        summary="One RTL module dispatches encrypt/decrypt based on the control-plane decrypt mode.",
        evidence=(
            "rtl/stream/ascon_aead128_stream.v",
            "rtl/stream/ascon_stream_file_list.f",
            "tests/test_aead128_stream_unified_rtl.py",
            "docs/streaming_aead_unified_backend.md",
        ),
    ),
    Milestone(
        key="firmware_stream_driver",
        title="Firmware driver stream sequencing and emulator",
        stage="firmware",
        summary="The C driver starts stream backends before payload transfer and has a host reference emulator/benchmark.",
        evidence=(
            "firmware/ascon_accel/ascon_accel.c",
            "firmware/ascon_accel/ascon_accel_axis_ref_emulator.c",
            "tools/run_firmware_stream_ref_benchmark.py",
            "tests/test_firmware_stream_ref_emulator.py",
            "tests/test_firmware_stream_ref_benchmark_tool.py",
        ),
    ),
    Milestone(
        key="axis_mmio_bridge",
        title="CPU-driven AXI-stream MMIO bridge",
        stage="rtl_integration",
        summary="Firmware can push/pop 128-bit stream beats through a register bridge with RX FIFO buffering.",
        evidence=(
            "firmware/ascon_accel/ascon_accel_axis_mmio_transport.c",
            "rtl/common/ascon_axis_mmio_bridge.v",
            "tools/run_axis_mmio_bridge_vector.py",
            "tests/test_axis_mmio_bridge_sim.py",
            "docs/axis_mmio_bridge_rtl.md",
        ),
        limitations=(
            "The CPU bridge is a bring-up transport; high-throughput board use should move to DMA.",
        ),
    ),
    Milestone(
        key="full_axis_mmio_system_sim",
        title="Integrated CSR + AXI-MMIO + stream backend simulation",
        stage="system_simulation",
        summary="The full board-facing subsystem is simulated through CSR and bridge MMIO accesses.",
        evidence=(
            "rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v",
            "tools/run_stream_axis_mmio_system_vector.py",
            "tests/test_stream_axis_mmio_system_sim.py",
            "docs/stream_axis_mmio_system_simulation.md",
        ),
    ),
    Milestone(
        key="neorv32_stream_firmware_mode",
        title="NEORV32 stream benchmark firmware mode",
        stage="neorv32",
        summary="The NEORV32 benchmark firmware can select the stream MMIO transport build mode.",
        evidence=(
            "firmware/neorv32_ascon_benchmark/main.c",
            "firmware/neorv32_ascon_benchmark/Makefile",
            "tests/test_neorv32_stream_benchmark_scaffold.py",
            "docs/firmware_axis_mmio_transport.md",
        ),
    ),
    Milestone(
        key="neorv32_cfs_wrapper",
        title="Stream-native NEORV32 CFS wrapper",
        stage="neorv32",
        summary="A VHDL CFS wrapper maps CSR and AXI-MMIO windows into one NEORV32 CFS region.",
        evidence=(
            "rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd",
            "rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f",
            "tests/test_neorv32_stream_cfs_integration.py",
            "docs/neorv32_stream_cfs_integration.md",
        ),
    ),
    Milestone(
        key="board_handoff",
        title="Tang Nano 9K NEORV32 board handoff package",
        stage="board_handoff",
        summary="Manifest, preflight, package, session, UART-report, build-plan, and Gowin handoff tooling are present.",
        evidence=(
            "boards/tangnano9k/neorv32_stream_axis_mmio/manifest.json",
            "tools/neorv32_stream_board_preflight.py",
            "tools/prepare_neorv32_stream_board_build.py",
            "tools/run_neorv32_stream_board_session.py",
            "tools/prepare_neorv32_stream_gowin_handoff.py",
            "tools/parse_neorv32_ascon_uart_log.py",
            "tests/test_neorv32_stream_gowin_handoff.py",
        ),
        limitations=(
            "The repo has not yet captured a real UART PASS log from a programmed Tang Nano board.",
            "The mixed-language Gowin/NEORV32 project must still be assembled in the board tool flow.",
        ),
    ),
)

REMAINING_WORK: tuple[dict[str, str], ...] = (
    {
        "priority": "P0",
        "item": "Real Tang Nano / NEORV32 build",
        "detail": "Integrate the VHDL CFS wrapper and Verilog ASCON subsystem into the actual NEORV32 SoC/Gowin project and produce a bitstream.",
    },
    {
        "priority": "P0",
        "item": "Board UART benchmark capture",
        "detail": "Program the board, run the NEORV32 benchmark firmware, capture UART output, and parse it with the strict UART report tool.",
    },
    {
        "priority": "P1",
        "item": "Hardware-vs-software performance proof",
        "detail": "Record cycles/byte and speedup from a real board run; keep the UART JSON/Markdown report as evidence.",
    },
    {
        "priority": "P1",
        "item": "DMA or deeper streaming transport",
        "detail": "Replace the CPU-polling AXI-MMIO bridge with DMA or a production stream transport for higher throughput.",
    },
    {
        "priority": "P2",
        "item": "High-throughput FPGA architecture",
        "detail": "Add the pipelined permutation / multi-context core family once board-level correctness is proven.",
    },
    {
        "priority": "P2",
        "item": "ASIC area-optimized family",
        "detail": "Add serial/5-bit S-box ASIC datapaths after the FPGA software/hardware integration path is stable.",
    },
)


def _exists(repo_root: Path, rel: str) -> bool:
    return (repo_root / rel).exists()


def _count_test_functions(test_dir: Path) -> dict[str, int]:
    files = sorted(test_dir.glob("test_*.py"))
    total = 0
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                total += 1
    return {"test_files": len(files), "test_functions": total}


def _milestone_status(repo_root: Path, milestone: Milestone) -> dict[str, Any]:
    evidence = [{"path": path, "exists": _exists(repo_root, path)} for path in milestone.evidence]
    complete = all(item["exists"] for item in evidence)
    return {
        "key": milestone.key,
        "title": milestone.title,
        "stage": milestone.stage,
        "status": "complete" if complete else "missing_evidence",
        "summary": milestone.summary,
        "evidence": evidence,
        "limitations": list(milestone.limitations),
    }


def generate_report(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    milestones = [_milestone_status(repo_root, milestone) for milestone in MILESTONES]
    complete = sum(1 for item in milestones if item["status"] == "complete")
    test_counts = _count_test_functions(repo_root / "tests")
    generated = {
        "docs_configs_dir": _exists(repo_root, "docs/generated"),
        "rtl_generated_dir": _exists(repo_root, "rtl/generated"),
        "board_package_tool": _exists(repo_root, "tools/prepare_neorv32_stream_board_build.py"),
        "gowin_handoff_tool": _exists(repo_root, "tools/prepare_neorv32_stream_gowin_handoff.py"),
    }
    return {
        "project": "pyrilascon ASCON FPGA/ASIC generator",
        "phase": "stream-native AEAD128 FPGA/NEORV32 bring-up handoff",
        "status": "ready_for_real_board_integration" if complete == len(milestones) else "incomplete_evidence",
        "milestone_count": len(milestones),
        "complete_milestones": complete,
        "milestones": milestones,
        "verification_inventory": test_counts,
        "generated_artifacts": generated,
        "next_gate": "real Tang Nano / NEORV32 build plus UART benchmark report",
        "remaining_work": list(REMAINING_WORK),
    }


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for milestone in report["milestones"]:
        if milestone["status"] != "complete":
            missing = [item["path"] for item in milestone["evidence"] if not item["exists"]]
            errors.append(f"{milestone['key']} missing evidence: {', '.join(missing)}")
    if report["verification_inventory"]["test_functions"] < 250:
        errors.append("unexpectedly low test inventory; expected at least 250 test functions")
    return errors


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# ASCON project status report",
        "",
        f"Project: `{report['project']}`",
        f"Phase: `{report['phase']}`",
        f"Status: `{report['status']}`",
        f"Next gate: **{report['next_gate']}**",
        "",
        "## Verification inventory",
        "",
        f"- Test files: `{report['verification_inventory']['test_files']}`",
        f"- Static pytest test functions: `{report['verification_inventory']['test_functions']}`",
        "- Simulator-dependent tests run when `iverilog`/`vvp` are installed.",
        "",
        "## Milestones",
        "",
    ]
    for milestone in report["milestones"]:
        lines.extend(
            [
                f"### {milestone['title']}",
                "",
                f"- Key: `{milestone['key']}`",
                f"- Stage: `{milestone['stage']}`",
                f"- Status: `{milestone['status']}`",
                f"- Summary: {milestone['summary']}",
                "- Evidence:",
            ]
        )
        for evidence in milestone["evidence"]:
            mark = "present" if evidence["exists"] else "missing"
            lines.append(f"  - `{evidence['path']}` — {mark}")
        if milestone["limitations"]:
            lines.append("- Limitations:")
            for item in milestone["limitations"]:
                lines.append(f"  - {item}")
        lines.append("")
    lines.extend(["## Remaining work", ""])
    for item in report["remaining_work"]:
        lines.append(f"- **{item['priority']} — {item['item']}**: {item['detail']}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The repository is ready for the first real Tang Nano / NEORV32 integration attempt, not for a final performance claim.",
            "A real board UART log parsed in strict mode is the next hard evidence gate.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    parser.add_argument("--markdown", action="store_true", help="print Markdown to stdout")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON_OUT, help="JSON output path")
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD_OUT, help="Markdown output path")
    parser.add_argument("--write-defaults", action="store_true", help="write default JSON and Markdown reports")
    parser.add_argument("--check", action="store_true", help="validate milestone evidence")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = generate_report(REPO_ROOT)
    errors = validate_report(report)
    if args.write_defaults:
        _write_json(args.out_json, report)
        _write_text(args.out_md, render_markdown(report))
    if args.check:
        if errors:
            for error in errors:
                print(f"error: {error}")
            return 1
        print("ok")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    if args.markdown:
        print(render_markdown(report))
    if not (args.write_defaults or args.check or args.json or args.markdown):
        _write_json(args.out_json, report)
        _write_text(args.out_md, render_markdown(report))
        print(f"wrote {args.out_json}")
        print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
