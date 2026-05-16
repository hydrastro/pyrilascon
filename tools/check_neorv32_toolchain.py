#!/usr/bin/env python3
"""Probe RISC-V bare-metal GCC compatibility for the NEORV32 firmware build.

The board benchmark needs a RISC-V bare-metal GCC that can link the NEORV32
firmware. A fully portable project cannot assume that every host provides the
same multilib layout: some toolchains support the hardware-correct RV32I/ILP32
profile, while the Nixpkgs embedded toolchain can expose a hard/double-float
newlib as its default library set.

This probe therefore tries three classes of profiles:

* ``soft``: hardware-correct NEORV32 RV32I/ILP32.
* ``hardfloat-nix``: explicit compatibility candidates for Nix-style toolchains.
* ``toolchain-default``: compile/link using the compiler's own default target,
  then recover the compiler-reported ``-march``/``-mabi`` for NEORV32 common.mk.

The last profile is intentionally a bring-up compatibility mode. It is useful
when the host toolchain can link only its default newlib/libgcc multilib. The
benchmark code itself is integer-only, but the final release build should still
prefer a true soft-float multilib toolchain when available.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SOFT_MARCH = "rv32i_zicsr_zifencei"
SOFT_MABI = "ilp32"
# Candidate order: prefer compact/canonical spellings that often match GCC's
# multilib table before the more explicit ISA strings.
HARDFLOAT_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("rv32gc", "ilp32d"),
    ("rv32imafdc", "ilp32d"),
    ("rv32imafdc_zicsr_zifencei", "ilp32d"),
)

# NEORV32 common.mk invokes more than gcc during the final image-generation
# phase. In Nix shells the gcc wrapper can exist while readelf is still missing
# if a previous shell created only the compiler aliases. Treat these as part of
# the toolchain contract so failures are caught before firmware linking.
REQUIRED_TOOLS: tuple[str, ...] = ("gcc", "objcopy", "readelf", "size")


@dataclass(frozen=True)
class ProbeResult:
    name: str
    march: str | None
    mabi: str | None
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    command: list[str]


@dataclass(frozen=True)
class ToolchainReport:
    prefix: str
    gcc: str | None
    required_tools: dict[str, str | None]
    soft: ProbeResult
    hardfloat: ProbeResult
    native: ProbeResult
    selected_profile: str | None
    selected_march: str | None
    selected_mabi: str | None
    warnings: list[str]
    errors: list[str]


TEST_PROGRAM = r"""
#include <stddef.h>
extern void *memset(void *, int, size_t);
volatile unsigned char sink[32];
int main(void) {
  memset((void *)sink, 0x5a, sizeof(sink));
  return (int)sink[0];
}
"""


def _short(text: str, limit: int = 800) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _probe_cmd(gcc: str, march: str | None, mabi: str | None, out: Path) -> list[str]:
    cmd = [gcc]
    if march:
        cmd.append(f"-march={march}")
    if mabi:
        cmd.append(f"-mabi={mabi}")
    cmd.extend(
        [
            "-Os",
            "-fno-builtin",
            "-ffunction-sections",
            "-fdata-sections",
            "-nostartfiles",
            "-Wl,--gc-sections",
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
    )
    return cmd


def _run_probe(gcc: str | None, name: str, march: str | None, mabi: str | None) -> ProbeResult:
    if gcc is None:
        return ProbeResult(name, march, mabi, False, 127, "", "compiler not found", [])

    with tempfile.TemporaryDirectory(prefix="neorv32_toolchain_probe_") as tmp:
        out = Path(tmp) / f"{name}.elf"
        cmd = _probe_cmd(gcc, march, mabi, out)
        completed = subprocess.run(
            cmd,
            input=TEST_PROGRAM,
            text=True,
            capture_output=True,
            check=False,
        )
        return ProbeResult(
            name=name,
            march=march,
            mabi=mabi,
            ok=completed.returncode == 0,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            command=cmd,
        )


def _default_target_from_gcc(gcc: str | None) -> tuple[str | None, str | None]:
    if gcc is None:
        return None, None
    completed = subprocess.run(
        [gcc, "-Q", "--help=target"],
        capture_output=True,
        text=True,
        check=False,
    )
    text = completed.stdout + "\n" + completed.stderr
    march: str | None = None
    mabi: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-march="):
            parts = stripped.split()
            if len(parts) >= 2 and parts[-1] != "[default]":
                march = parts[-1]
        elif stripped.startswith("-mabi="):
            parts = stripped.split()
            if len(parts) >= 2 and parts[-1] != "[default]":
                mabi = parts[-1]
    return march, mabi


def _candidate_from_multilib_line(line: str) -> tuple[str, str] | None:
    # Example: rv32imafdc/ilp32d;@march=rv32imafdc@mabi=ilp32d
    if "@march=" not in line or "@mabi=" not in line:
        return None
    march_match = re.search(r"@march=([^@\s]+)", line)
    mabi_match = re.search(r"@mabi=([^@\s]+)", line)
    if not march_match or not mabi_match:
        return None
    return march_match.group(1), mabi_match.group(1)


def _multilib_candidates(gcc: str | None) -> list[tuple[str, str]]:
    if gcc is None:
        return []
    completed = subprocess.run(
        [gcc, "-print-multi-lib"],
        capture_output=True,
        text=True,
        check=False,
    )
    candidates: list[tuple[str, str]] = []
    for line in completed.stdout.splitlines():
        parsed = _candidate_from_multilib_line(line.strip())
        if parsed is not None and parsed not in candidates:
            candidates.append(parsed)
    return candidates


def _first_ok(gcc: str | None, name: str, candidates: Iterable[tuple[str, str]]) -> ProbeResult:
    last: ProbeResult | None = None
    for index, (march, mabi) in enumerate(candidates):
        result = _run_probe(gcc, f"{name}_{index}", march, mabi)
        if result.ok:
            return ProbeResult(name, march, mabi, True, result.returncode, result.stdout, result.stderr, result.command)
        last = result
    if last is not None:
        return ProbeResult(name, last.march, last.mabi, False, last.returncode, last.stdout, last.stderr, last.command)
    return _run_probe(gcc, name, None, None)


def build_report(prefix: str, requested_profile: str) -> ToolchainReport:
    required_tools = {tool: shutil.which(f"{prefix}{tool}") for tool in REQUIRED_TOOLS}
    gcc = required_tools["gcc"]
    default_march, default_mabi = _default_target_from_gcc(gcc)

    soft = _run_probe(gcc, "soft", SOFT_MARCH, SOFT_MABI)

    hard_candidates: list[tuple[str, str]] = []
    for candidate in (*HARDFLOAT_CANDIDATES, *_multilib_candidates(gcc)):
        if candidate not in hard_candidates:
            hard_candidates.append(candidate)
    hardfloat = _first_ok(gcc, "hardfloat", hard_candidates)

    native_raw = _run_probe(gcc, "toolchain_default", None, None)
    native = ProbeResult(
        name="toolchain-default",
        march=default_march,
        mabi=default_mabi,
        ok=native_raw.ok and default_march is not None and default_mabi is not None,
        returncode=native_raw.returncode,
        stdout=native_raw.stdout,
        stderr=native_raw.stderr,
        command=native_raw.command,
    )

    warnings: list[str] = []
    errors: list[str] = []
    selected_profile: str | None = None
    selected_march: str | None = None
    selected_mabi: str | None = None

    missing_required = [tool for tool, path in required_tools.items() if path is None]
    if missing_required:
        errors.append(
            "missing required RISC-V toolchain programs: "
            + ", ".join(f"{prefix}{tool}" for tool in missing_required)
        )
    if gcc is None:
        errors.append(f"{prefix}gcc not found")
    elif requested_profile == "soft":
        if soft.ok:
            selected_profile, selected_march, selected_mabi = "soft", soft.march, soft.mabi
        else:
            errors.append(
                "toolchain cannot link NEORV32 soft-float RV32I/ILP32 firmware; "
                "install a multilib riscv-none-elf toolchain such as xPack or use NEORV32_FW_PROFILE=auto/toolchain-default for local bring-up"
            )
    elif requested_profile == "hardfloat-nix":
        if hardfloat.ok:
            selected_profile, selected_march, selected_mabi = "hardfloat-nix", hardfloat.march, hardfloat.mabi
            warnings.append(
                "using an explicit hard/double-float ABI compatibility profile for a package-manager toolchain; "
                "the benchmark code is integer-only, but a true soft-float multilib toolchain is preferred for final hardware release"
            )
        else:
            errors.append("hardfloat-nix compatibility profile did not link with this toolchain")
    elif requested_profile == "toolchain-default":
        if native.ok:
            selected_profile, selected_march, selected_mabi = "toolchain-default", native.march, native.mabi
            warnings.append(
                "using the compiler default RISC-V target because explicit NEORV32 soft-float linking is unavailable; "
                "verify the generated assembly before final release if your NEORV32 hardware omits F/D extensions"
            )
        else:
            errors.append("compiler default target did not link or did not report both -march and -mabi")
    elif requested_profile == "auto":
        if soft.ok:
            selected_profile, selected_march, selected_mabi = "soft", soft.march, soft.mabi
        elif hardfloat.ok:
            selected_profile, selected_march, selected_mabi = "hardfloat-nix", hardfloat.march, hardfloat.mabi
            warnings.append(
                "soft-float RV32I/ILP32 newlib is unavailable; falling back to an explicit hard/double-float ABI compatibility profile for this host toolchain"
            )
        elif native.ok:
            selected_profile, selected_march, selected_mabi = "toolchain-default", native.march, native.mabi
            warnings.append(
                "soft-float and explicit hardfloat probes failed; falling back to the compiler default target for host-toolchain compatibility"
            )
        else:
            errors.append(
                "toolchain cannot link soft-float, explicit hardfloat, or compiler-default profiles"
            )
    else:
        errors.append(f"unknown profile: {requested_profile}")

    if missing_required:
        selected_profile = None
        selected_march = None
        selected_mabi = None

    return ToolchainReport(
        prefix=prefix,
        gcc=gcc,
        required_tools=required_tools,
        soft=soft,
        hardfloat=hardfloat,
        native=native,
        selected_profile=selected_profile,
        selected_march=selected_march,
        selected_mabi=selected_mabi,
        warnings=warnings,
        errors=errors,
    )


def _profile_line(label: str, result: ProbeResult) -> str:
    march = result.march or "<compiler default>"
    mabi = result.mabi or "<compiler default>"
    return f"  {label:<18} {result.ok} march={march} mabi={mabi}"


def render_text(report: ToolchainReport, verbose: bool = False) -> str:
    lines = [
        "name: neorv32_toolchain_probe",
        f"prefix: {report.prefix}",
        f"gcc: {report.gcc or 'not found'}",
        "",
        "required tools:",
        *(f"  {report.prefix}{tool}: {path or 'not found'}" for tool, path in report.required_tools.items()),
        "",
        "profiles:",
        _profile_line("soft:", report.soft),
        _profile_line("hardfloat:", report.hardfloat),
        _profile_line("toolchain-default:", report.native),
        "",
        f"selected: {report.selected_profile or 'none'}",
    ]
    if report.selected_march and report.selected_mabi:
        lines.append(f"selected args: MARCH={report.selected_march} MABI={report.selected_mabi}")
    if report.warnings:
        lines.append("")
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in report.warnings)
    if report.errors:
        lines.append("")
        lines.append("errors:")
        lines.extend(f"  - {error}" for error in report.errors)
    if verbose or report.selected_profile is None:
        lines.append("")
        lines.append("last probe diagnostics:")
        for label, probe in (("soft", report.soft), ("hardfloat", report.hardfloat), ("toolchain-default", report.native)):
            lines.append(f"  {label}: returncode={probe.returncode}")
            if probe.stderr:
                lines.append(f"    stderr: {_short(probe.stderr)}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="riscv-none-elf-", help="RISC-V GCC toolchain prefix")
    parser.add_argument(
        "--profile",
        choices=["auto", "soft", "hardfloat-nix", "toolchain-default"],
        default="auto",
        help="requested firmware ABI profile",
    )
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--make-args", action="store_true", help="print MARCH/MABI make arguments only")
    parser.add_argument("--check", action="store_true", help="return nonzero when no usable profile is selected")
    parser.add_argument("--verbose", action="store_true", help="include linker diagnostics even when a profile is selected")
    args = parser.parse_args(argv)

    report = build_report(prefix=args.prefix, requested_profile=args.profile)

    if args.make_args:
        if report.selected_profile is None or report.selected_march is None or report.selected_mabi is None:
            print(render_text(report, verbose=True), file=sys.stderr)
            return 1
        print(f"MARCH={report.selected_march} MABI={report.selected_mabi}")
    elif args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(render_text(report, verbose=args.verbose), end="")

    if args.check and report.selected_profile is None:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
