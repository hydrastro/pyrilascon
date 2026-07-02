#!/usr/bin/env python3
"""Fail when known machine-local or duplicate artifacts pollute the source tree."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATHS = [
    ROOT / "boards/tangnano20k/neorv32_mmio/.venv-fpga",
    ROOT / "boards/tangnano20k/neorv32_mmio/external",
    ROOT / "mnt",
    ROOT / "uart.log",
    ROOT / "cosim_report.md",
    ROOT / "ascon_accel.o",
    ROOT / "main_demo.o",
    ROOT / "rtl/stream/ascon_aead128_stream_decrypt_buffered.v.bak",
    ROOT / "boards/tangnano9k/neorv32_stream_axis_mmio/sys",
    ROOT / "boards/tangnano9k/neorv32_mmio/cosim/neorv32_verilog_wrapper.v",
    ROOT / "firmware/ascon_accel/.gitignore",
    ROOT / "firmware/ascon_accel/Makefile",
    ROOT / "firmware/ascon_accel/flake.nix",
    ROOT / "firmware/ascon_accel/flake.lock",
    ROOT / "firmware/ascon_accel/pytest.ini",
]
NESTED_REPO_NAMES = [
    "ascon_arch",
    "ascon_hwmodel",
    "benchmarks",
    "boards",
    "configs",
    "docs",
    "firmware",
    "rtl",
    "tests",
    "tools",
    "vectors",
]


def audit() -> list[str]:
    issues: list[str] = []
    for path in FORBIDDEN_PATHS:
        if path.exists():
            issues.append(f"forbidden generated/accidental path: {path.relative_to(ROOT)}")

    driver_dir = ROOT / "firmware/ascon_accel"
    for name in NESTED_REPO_NAMES:
        path = driver_dir / name
        if path.exists():
            issues.append(f"duplicate nested repository subtree: {path.relative_to(ROOT)}")

    for path in (ROOT / "firmware/ascon_accel").glob("demo_*.py"):
        issues.append(f"duplicate nested repository file: {path.relative_to(ROOT)}")

    for path in ROOT.rglob("*.gch"):
        issues.append(f"precompiled header artifact: {path.relative_to(ROOT)}")
    for path in ROOT.rglob("*.bak"):
        issues.append(f"backup artifact: {path.relative_to(ROOT)}")

    # A root-local .venv-fpga and external/neorv32 are reproducible, ignored
    # developer dependencies and are intentionally allowed.
    return sorted(set(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    issues = audit()
    if args.json:
        print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
    elif issues:
        print("Repository hygiene: FAIL")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Repository hygiene: PASS")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
