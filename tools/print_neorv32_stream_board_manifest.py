#!/usr/bin/env python3
"""Inspect the Tang Nano 9K NEORV32 stream ASCON board manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "manifest.json"


class ManifestError(RuntimeError):
    """Raised when the board manifest is inconsistent."""


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_path(relpath: str) -> None:
    path = REPO_ROOT / relpath
    if not path.exists():
        raise ManifestError(f"manifest references missing path: {relpath}")


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise ManifestError("unsupported manifest schema_version")

    memory = manifest["memory_map"]
    cfs_base = int(memory["ascon_cfs_base"], 16)
    csr_base = int(memory["csr_window"]["base"], 16)
    axis_base = int(memory["axis_mmio_window"]["base"], 16)
    csr_offset = int(memory["csr_window"]["offset"], 16)
    axis_offset = int(memory["axis_mmio_window"]["offset"], 16)

    if csr_base != cfs_base + csr_offset:
        raise ManifestError("CSR base does not match CFS base + CSR offset")
    if axis_base != cfs_base + axis_offset:
        raise ManifestError("AXI-MMIO base does not match CFS base + AXI offset")
    if memory["csr_window"]["size_bytes"] != 256 or memory["axis_mmio_window"]["size_bytes"] != 256:
        raise ManifestError("CSR and AXI-MMIO windows must be 256 bytes each")
    if axis_offset != 0x100:
        raise ManifestError("stream CFS wrapper expects AXI-MMIO window at offset 0x100")

    top = manifest["top"]
    _require_path(top["cfs_wrapper"])
    _require_path(top["accelerator_system"])

    rtl = manifest["rtl"]
    _require_path(rtl["primary_file_list"])
    for source in rtl["required_sources"]:
        _require_path(source)

    firmware = manifest["firmware"]
    _require_path(firmware["directory"])
    if firmware["make_mode"] != "USE_CFS_AXIS_MMIO=1":
        raise ManifestError("firmware make_mode must select the single-CFS stream map")
    defines = firmware["defines"]
    if defines["ASCON_ACCEL_BASE_ADDR"].lower() != "0xffeb0000u":
        raise ManifestError("unexpected ASCON_ACCEL_BASE_ADDR")
    if defines["ASCON_ACCEL_AXIS_MMIO_BASE_ADDR"].lower() != "0xffeb0100u":
        raise ManifestError("unexpected ASCON_ACCEL_AXIS_MMIO_BASE_ADDR")


def render_text(manifest: dict[str, Any]) -> str:
    memory = manifest["memory_map"]
    rtl = manifest["rtl"]
    firmware = manifest["firmware"]
    lines = [
        f"name: {manifest['name']}",
        f"board: {manifest['board']['name']} ({manifest['board']['fpga_family']})",
        f"status: {manifest['board']['status']}",
        "",
        "memory map:",
        f"  CSR       {memory['csr_window']['base']} + {memory['csr_window']['offset']} size={memory['csr_window']['size_bytes']} bytes",
        f"  AXI-MMIO  {memory['axis_mmio_window']['base']} + {memory['axis_mmio_window']['offset']} size={memory['axis_mmio_window']['size_bytes']} bytes",
        "",
        "rtl:",
        f"  cfs wrapper: {manifest['top']['cfs_wrapper']}",
        f"  file list:   {rtl['primary_file_list']}",
        "",
        "firmware:",
        f"  directory: {firmware['directory']}",
        f"  mode:      {firmware['make_mode']}",
        f"  command:   {firmware['command']}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", help="print raw manifest JSON")
    parser.add_argument("--check", action="store_true", help="validate the manifest and print ok")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    validate_manifest(manifest)

    if args.check:
        print("ok")
    elif args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(render_text(manifest))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
