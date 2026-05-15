#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ascon_arch.design_product import write_design_product
from ascon_arch.enums import TargetTechnology
from ascon_arch.matrix import (
    ASIC_DATAPATH_MATRIX,
    ASIC_PERMUTATION_MATRIX,
    FPGA_DATAPATH_MATRIX,
    FPGA_PERMUTATION_MATRIX,
    enumerate_valid_matrix,
)


def build_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate a matrix of valid ASCON architecture products.")
    parser.add_argument("--target", choices=("asic", "fpga", "both"), default="both")
    parser.add_argument("--engine-count", type=int, default=4, help="Engine count for FPGA matrix entries.")
    parser.add_argument("--out", type=Path, default=Path("build/matrix"))
    parser.add_argument("--write-invalid-report", action="store_true", help="Write matrix_report.json including skipped invalid combinations.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    targets = []
    if args.target in ("asic", "both"):
        targets.append(TargetTechnology.ASIC)
    if args.target in ("fpga", "both"):
        targets.append(TargetTechnology.FPGA)

    all_entries = []
    for target in targets:
        if target == TargetTechnology.ASIC:
            entries = enumerate_valid_matrix(
                target,
                ASIC_DATAPATH_MATRIX,
                ASIC_PERMUTATION_MATRIX,
                engine_count=args.engine_count,
            )
        else:
            entries = enumerate_valid_matrix(
                target,
                FPGA_DATAPATH_MATRIX,
                FPGA_PERMUTATION_MATRIX,
                engine_count=args.engine_count,
            )
        all_entries.extend(entries)

    for entry in all_entries:
        if entry.valid and entry.config is not None:
            for path in write_design_product(entry.config, args.out):
                print(path)

    if args.write_invalid_report:
        args.out.mkdir(parents=True, exist_ok=True)
        report_path = args.out / "matrix_report.json"
        report_path.write_text(
            json.dumps([entry.to_dict() for entry in all_entries], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(report_path)


if __name__ == "__main__":
    main()
