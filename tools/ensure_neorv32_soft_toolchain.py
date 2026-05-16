#!/usr/bin/env python3
"""Ensure a project-local NEORV32-compatible RV32I/ILP32 GCC toolchain.

The Nixpkgs ``riscv32-none-elf`` toolchain can link firmware using its own
hard/double-float newlib multilib, which is useful for host-side smoke tests but
is not the hardware-correct default for a minimal NEORV32 soft core.  NEORV32's
normal software profile is RV32I/ILP32, so board-release firmware should prefer
a toolchain that can link ``-march=rv32i_zicsr_zifencei -mabi=ilp32``.

This helper keeps that dependency inside the repository under ``external/``.
It accepts an existing toolchain directory, or can download/extract the official
NEORV32 prebuilt RV32I/ILP32 GCC archive for x86_64 Linux. The helper does not
pull any unfree compatibility runtime into the Nix shell. On NixOS, the
downloaded generic Linux binaries may require a system-provided compatibility
layer such as nix-ld or an FHS shell; the helper detects that case and reports it
cleanly.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_URL = "https://github.com/stnolting/riscv-gcc-prebuilt/releases/download/rv32i-131023/riscv32-unknown-elf.gcc-13.2.0.tar.gz"
DEFAULT_DIR = Path("external") / "riscv32-unknown-elf-gcc-rv32i-ilp32"
PREFIX_NAME = "riscv32-unknown-elf-"
REQUIRED_TOOLS = ("gcc", "objcopy", "readelf", "size")


@dataclass(frozen=True)
class SoftToolchainReport:
    directory: str
    prefix: str | None
    ready: bool
    missing_tools: list[str]
    source: str
    note: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_dir(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (_repo_root() / path).resolve()


def _prefix_has_required_tools(prefix: Path) -> bool:
    return all((Path(f"{prefix}{tool}").exists() and os.access(Path(f"{prefix}{tool}"), os.X_OK)) for tool in REQUIRED_TOOLS)


def _find_prefix(directory: Path) -> Path | None:
    if not directory.exists():
        return None
    candidates = sorted(directory.rglob(f"{PREFIX_NAME}gcc"))
    for gcc in candidates:
        if gcc.is_file() and os.access(gcc, os.X_OK):
            prefix = gcc.parent / PREFIX_NAME
            if _prefix_has_required_tools(prefix):
                return prefix
    return None


def _missing_tools(prefix: Path | None) -> list[str]:
    if prefix is None:
        return list(REQUIRED_TOOLS)
    missing: list[str] = []
    for tool in REQUIRED_TOOLS:
        path = Path(f"{prefix}{tool}")
        if not (path.exists() and os.access(path, os.X_OK)):
            missing.append(tool)
    return missing


def build_report(directory: Path = DEFAULT_DIR) -> SoftToolchainReport:
    resolved = _resolve_dir(directory)
    prefix = _find_prefix(resolved)
    missing = _missing_tools(prefix)
    ready = prefix is not None and not missing
    if ready:
        note = "RV32I/ILP32 soft-float toolchain found."
    elif not resolved.exists():
        note = "toolchain directory does not exist; run with --fetch to download it."
    else:
        note = "toolchain directory exists but required programs are missing."
    return SoftToolchainReport(
        directory=str(resolved),
        prefix=str(prefix) if prefix is not None else None,
        ready=ready,
        missing_tools=missing,
        source=DEFAULT_URL,
        note=note,
    )


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _extract(archive: Path, directory: Path, clean: bool) -> None:
    if clean and directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        def safe_members():
            root = directory.resolve()
            for member in tar.getmembers():
                target = (directory / member.name).resolve()
                if not str(target).startswith(str(root) + os.sep) and target != root:
                    raise RuntimeError(f"unsafe path in archive: {member.name}")
                yield member
        tar.extractall(directory, members=safe_members())


def fetch_toolchain(directory: Path, url: str, clean: bool) -> SoftToolchainReport:
    resolved = _resolve_dir(directory)
    before = build_report(resolved)
    if before.ready and not clean:
        return before
    with tempfile.TemporaryDirectory(prefix="neorv32_soft_toolchain_") as tmp:
        archive = Path(tmp) / "toolchain.tar.gz"
        _download(url, archive)
        _extract(archive, resolved, clean=clean)
    return build_report(resolved)


def _is_nixos_dynamic_loader_error(text: str) -> bool:
    return "NixOS cannot run dynamically linked executables" in text or "stub-ld" in text


def _verify_soft_prefix(prefix: str) -> tuple[bool, str]:
    gcc = f"{prefix}gcc"
    if not Path(gcc).exists() and not shutil.which(gcc):
        return False, f"{gcc} not found"
    program = "int main(void) { return 0; }\n"
    with tempfile.TemporaryDirectory(prefix="neorv32_soft_probe_") as tmp:
        out = Path(tmp) / "probe.elf"
        cmd = [
            gcc,
            "-march=rv32i_zicsr_zifencei",
            "-mabi=ilp32",
            "-nostartfiles",
            "-Wl,-e,main",
            "-Wl,-Ttext=0x0",
            "-x",
            "c",
            "-",
            "-o",
            str(out),
            "-lc",
            "-lgcc",
        ]
        completed = subprocess.run(cmd, input=program, text=True, capture_output=True, check=False)
        if completed.returncode == 0:
            return True, "soft-float RV32I/ILP32 link probe passed"
        return False, completed.stderr.strip() or completed.stdout.strip() or f"returncode={completed.returncode}"


def render_text(report: SoftToolchainReport, verify_note: str | None = None) -> str:
    lines = [
        "name: neorv32_soft_toolchain",
        f"ready: {report.ready}",
        f"directory: {report.directory}",
        f"prefix: {report.prefix or 'not found'}",
        f"source: {report.source}",
        f"note: {report.note}",
    ]
    if report.missing_tools:
        lines.append("missing tools:")
        lines.extend(f"  - {tool}" for tool in report.missing_tools)
    if verify_note is not None:
        lines.append(f"soft link probe: {verify_note}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-prefix", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verify-link", action="store_true")
    args = parser.parse_args(argv)

    if args.fetch:
        report = fetch_toolchain(args.toolchain_dir, args.url, clean=args.clean)
    else:
        report = build_report(args.toolchain_dir)

    verify_ok = True
    verify_note: str | None = None
    if args.verify_link and report.prefix is not None:
        verify_ok, verify_note = _verify_soft_prefix(report.prefix)
        if not verify_ok and verify_note is not None and _is_nixos_dynamic_loader_error(verify_note):
            verify_note = (
                verify_note
                + "\nNixOS note: the downloaded official Linux toolchain is dynamically linked and "
                + "cannot execute in a plain Nix shell. Configure nix-ld/FHS compatibility "
                + "or provide an executable RV32I/ILP32 toolchain prefix; the project does "
                + "not add unfree runtime dependencies automatically."
            )
    elif args.verify_link:
        verify_ok, verify_note = False, "prefix not found"

    if args.print_prefix:
        if report.prefix is None:
            print(render_text(report, verify_note), file=sys.stderr)
            return 1
        print(report.prefix)
    elif args.json:
        payload = asdict(report)
        if verify_note is not None:
            payload["soft_link_probe"] = {"ok": verify_ok, "note": verify_note}
        print(json.dumps(payload, indent=2))
    else:
        print(render_text(report, verify_note), end="")

    if args.check and (not report.ready or not verify_ok):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
