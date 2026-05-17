#!/usr/bin/env python3
"""Generate an archiveable project checkpoint bundle for the current ASCON development stage."""
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from generate_project_status_report import generate_report, render_markdown, validate_report
from print_neorv32_stream_board_manifest import DEFAULT_MANIFEST, load_manifest, validate_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "build" / "project_checkpoint_bundle"
DEFAULT_ZIP = REPO_ROOT / "build" / "project_checkpoint_bundle.zip"

CORE_REPORT_FILES = (
    "README.md",
    "docs/project_development_summary.md",
    "docs/project_status_report.md",
    "docs/neorv32_stream_board_manifest.md",
    "docs/neorv32_stream_board_preflight.md",
    "docs/neorv32_stream_board_package.md",
    "docs/neorv32_stream_board_build_plan.md",
    "docs/neorv32_stream_board_session.md",
    "docs/neorv32_stream_gowin_handoff.md",
    "docs/neorv32_uart_benchmark_report.md",
    "docs/streaming_aead_contract.md",
    "docs/streaming_aead_soc_top.md",
    "docs/axis_mmio_bridge_rtl.md",
    "docs/stream_axis_mmio_system_simulation.md",
    "boards/tangnano9k/neorv32_stream_axis_mmio/manifest.json",
    "boards/tangnano9k/neorv32_stream_axis_mmio/README.md",
    "boards/tangnano9k/neorv32_stream_axis_mmio/Makefile",
    "rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f",
    "rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd",
    "firmware/neorv32_ascon_benchmark/README.md",
    "firmware/neorv32_ascon_benchmark/Makefile",
)

OPTIONAL_BUILD_ARTIFACTS = (
    "build/project_status/project_status.json",
    "build/project_status/project_status.md",
    "build/neorv32_stream_axis_mmio/preflight.json",
    "build/neorv32_stream_axis_mmio/package/package.json",
    "build/neorv32_stream_axis_mmio/package/memory_map.json",
    "build/neorv32_stream_axis_mmio/build_plan.json",
    "build/neorv32_stream_axis_mmio/build_plan.md",
    "build/neorv32_stream_axis_mmio/gowin_handoff/handoff.json",
    "build/neorv32_stream_axis_mmio/gowin_handoff/README.md",
)


class CheckpointBundleError(RuntimeError):
    """Raised when the checkpoint bundle cannot be generated or validated."""


@dataclass(frozen=True)
class CopiedFile:
    source: str
    bundle_path: str
    required: bool
    size_bytes: int


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _copy_relpath(relpath: str, out_dir: Path, *, required: bool) -> CopiedFile | None:
    src = REPO_ROOT / relpath
    if not src.exists():
        if required:
            raise CheckpointBundleError(f"required checkpoint source is missing: {relpath}")
        return None
    if src.is_dir():
        raise CheckpointBundleError(f"checkpoint source must be a file, not directory: {relpath}")
    dst = out_dir / "files" / relpath
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return CopiedFile(source=relpath, bundle_path=dst.relative_to(out_dir).as_posix(), required=required, size_bytes=dst.stat().st_size)


def _milestone_evidence(report: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    paths: list[str] = []
    for milestone in report["milestones"]:
        for evidence in milestone["evidence"]:
            relpath = evidence["path"]
            if relpath not in seen:
                seen.add(relpath)
                paths.append(relpath)
    return paths


def _makefile_targets() -> dict[str, bool]:
    root_makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    board_makefile = (REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile").read_text(encoding="utf-8")
    targets = {
        "root:test": "test:" in root_makefile,
        "root:verify": "verify:" in root_makefile,
        "root:stream-encrypt-sim": "stream-encrypt-sim:" in root_makefile,
        "root:stream-decrypt-sim": "stream-decrypt-sim:" in root_makefile,
        "root:stream-axis-mmio-system-sim": "stream-axis-mmio-system-sim:" in root_makefile,
        "root:project-status-report": "project-status-report:" in root_makefile,
        "root:project-checkpoint-bundle": "project-checkpoint-bundle:" in root_makefile,
        "board:package": "package:" in board_makefile,
        "board:build-plan": "build-plan:" in board_makefile,
        "board:session": "session:" in board_makefile,
        "board:gowin-handoff": "gowin-handoff:" in board_makefile,
        "board:firmware": "firmware:" in board_makefile,
        "board:prog-sram": "prog-sram:" in board_makefile,
    }
    return targets


def build_checkpoint(out_dir: Path = DEFAULT_OUT_DIR, zip_out: Path = DEFAULT_ZIP, *, clean: bool = False) -> dict[str, Any]:
    report = generate_report(REPO_ROOT)
    errors = validate_report(report)
    if errors:
        raise CheckpointBundleError("project status report is not valid: " + "; ".join(errors))

    manifest = load_manifest(DEFAULT_MANIFEST)
    validate_manifest(manifest)

    if clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_json(out_dir / "project_status.json", report)
    _write_text(out_dir / "project_status.md", render_markdown(report))
    _write_json(out_dir / "board_manifest.json", manifest)

    copied: list[CopiedFile] = []
    required_paths: list[str] = []
    for relpath in [*CORE_REPORT_FILES, *_milestone_evidence(report)]:
        if relpath not in required_paths:
            required_paths.append(relpath)
    for relpath in required_paths:
        item = _copy_relpath(relpath, out_dir, required=True)
        if item is not None:
            copied.append(item)
    for relpath in OPTIONAL_BUILD_ARTIFACTS:
        item = _copy_relpath(relpath, out_dir, required=False)
        if item is not None:
            copied.append(item)

    targets = _makefile_targets()
    missing_targets = [name for name, present in targets.items() if not present]
    if missing_targets:
        raise CheckpointBundleError("Makefile set is missing checkpoint targets: " + ", ".join(missing_targets))

    metadata = {
        "schema_version": 1,
        "name": "pyrilascon_project_checkpoint_bundle",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project_status": report["status"],
        "next_gate": report["next_gate"],
        "milestones_complete": report["complete_milestones"],
        "milestones_total": report["milestone_count"],
        "board_manifest": manifest["name"],
        "memory_map": {
            "ascon_cfs_base": manifest["memory_map"]["ascon_cfs_base"],
            "csr_base": manifest["memory_map"]["csr_window"]["base"],
            "axis_mmio_base": manifest["memory_map"]["axis_mmio_window"]["base"],
        },
        "makefile_targets": targets,
        "copied_files": [item.__dict__ for item in copied],
        "generated_files": [
            "checkpoint.json",
            "checkpoint.md",
            "project_status.json",
            "project_status.md",
            "board_manifest.json",
            "files/",
        ],
        "archive": str(zip_out),
    }

    _write_json(out_dir / "checkpoint.json", metadata)
    _write_text(out_dir / "checkpoint.md", render_checkpoint_markdown(metadata, report))

    zip_out.parent.mkdir(parents=True, exist_ok=True)
    if zip_out.exists():
        zip_out.unlink()
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(out_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(out_dir).as_posix())

    validate_checkpoint(out_dir, zip_out)
    return metadata


def render_checkpoint_markdown(metadata: dict[str, Any], report: dict[str, Any]) -> str:
    memory = metadata["memory_map"]
    lines = [
        "# pyrilascon project checkpoint bundle",
        "",
        f"Status: `{metadata['project_status']}`",
        f"Milestones complete: **{metadata['milestones_complete']} / {metadata['milestones_total']}**",
        f"Next gate: **{metadata['next_gate']}**",
        "",
        "## Board target",
        "",
        f"- Manifest: `{metadata['board_manifest']}`",
        f"- CFS base: `{memory['ascon_cfs_base']}`",
        f"- CSR base: `{memory['csr_base']}`",
        f"- AXI-MMIO base: `{memory['axis_mmio_base']}`",
        "",
        "## Included evidence",
        "",
    ]
    by_stage: dict[str, list[dict[str, Any]]] = {}
    for milestone in report["milestones"]:
        by_stage.setdefault(milestone["stage"], []).append(milestone)
    for stage, milestones in sorted(by_stage.items()):
        lines.append(f"### {stage}")
        lines.append("")
        for milestone in milestones:
            lines.append(f"- **{milestone['title']}** — {milestone['summary']}")
        lines.append("")
    lines.extend(
        [
            "## Remaining gates",
            "",
            *[f"- **{item['priority']} {item['item']}**: {item['detail']}" for item in report["remaining_work"]],
            "",
            "## Archive contents",
            "",
            "- `checkpoint.json` / `checkpoint.md`: bundle metadata",
            "- `project_status.json` / `project_status.md`: implementation status snapshot",
            "- `board_manifest.json`: Tang Nano 9K NEORV32 stream memory-map contract",
            "- `files/`: copied source/docs/tests evidence paths",
            "",
            "Regenerate with:",
            "",
            "```sh",
            "make project-checkpoint-bundle",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def validate_checkpoint(out_dir: Path = DEFAULT_OUT_DIR, zip_out: Path = DEFAULT_ZIP) -> None:
    required = [
        out_dir / "checkpoint.json",
        out_dir / "checkpoint.md",
        out_dir / "project_status.json",
        out_dir / "project_status.md",
        out_dir / "board_manifest.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise CheckpointBundleError("checkpoint bundle is missing files: " + ", ".join(missing))
    metadata = json.loads((out_dir / "checkpoint.json").read_text(encoding="utf-8"))
    if metadata["project_status"] != "ready_for_real_board_integration":
        raise CheckpointBundleError(f"unexpected checkpoint status: {metadata['project_status']}")
    if metadata["milestones_complete"] != metadata["milestones_total"]:
        raise CheckpointBundleError("checkpoint has incomplete milestones")
    if not (out_dir / "files" / "README.md").exists():
        raise CheckpointBundleError("checkpoint evidence copy is missing README.md")
    if not zip_out.exists() or zip_out.stat().st_size == 0:
        raise CheckpointBundleError(f"checkpoint archive was not created: {zip_out}")
    with zipfile.ZipFile(zip_out) as zf:
        names = set(zf.namelist())
    for name in ["checkpoint.json", "checkpoint.md", "project_status.json", "board_manifest.json", "files/README.md"]:
        if name not in names:
            raise CheckpointBundleError(f"checkpoint archive missing member: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--zip-out", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--clean", action="store_true", help="remove the checkpoint directory before generating")
    parser.add_argument("--check", action="store_true", help="validate an existing checkpoint bundle and print ok")
    parser.add_argument("--write-defaults", action="store_true", help="generate the default checkpoint directory and archive")
    parser.add_argument("--json", action="store_true", help="print generated checkpoint metadata as JSON")
    args = parser.parse_args()

    try:
        if args.check:
            validate_checkpoint(args.out_dir, args.zip_out)
            print("ok")
            return 0
        if args.write_defaults or args.json:
            metadata = build_checkpoint(args.out_dir, args.zip_out, clean=args.clean)
            if args.json:
                print(json.dumps(metadata, indent=2, sort_keys=True))
            return 0
        metadata = build_checkpoint(args.out_dir, args.zip_out, clean=args.clean)
        print(f"wrote {args.out_dir}")
        print(f"wrote {args.zip_out}")
        print(f"status {metadata['project_status']}")
        return 0
    except CheckpointBundleError as exc:
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
