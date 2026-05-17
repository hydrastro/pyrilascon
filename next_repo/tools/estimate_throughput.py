#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ascon_arch import (
    PermutationProfile,
    TargetTechnology,
    permutation_config_for_profile,
)
from ascon_arch.benchmarking import AeadBenchmarkShape, throughput_estimate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate AEAD128 throughput for one permutation profile.")
    parser.add_argument("--permutation-profile", required=True, choices=[item.value for item in PermutationProfile])
    parser.add_argument("--target", default="fpga", choices=[item.value for item in TargetTechnology])
    parser.add_argument("--clock-mhz", type=float, required=True)
    parser.add_argument("--ad-bytes", type=int, default=32)
    parser.add_argument("--text-bytes", type=int, default=1024)
    parser.add_argument("--data-bus-bits", type=int, default=128)
    parser.add_argument("--contexts", type=int, default=1)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = PermutationProfile(args.permutation_profile)
    target = TargetTechnology(args.target)
    permutation = permutation_config_for_profile(profile, target)
    shape = AeadBenchmarkShape(args.ad_bytes, args.text_bytes)
    estimate = throughput_estimate(
        permutation,
        shape,
        clock_mhz=args.clock_mhz,
        data_bus_bits=args.data_bus_bits,
        contexts_available=args.contexts,
    )
    payload = {
        "permutation_profile": profile.value,
        "target": target.value,
        "clock_mhz": args.clock_mhz,
        "ad_bytes": args.ad_bytes,
        "text_bytes": args.text_bytes,
        "data_bus_bits": args.data_bus_bits,
        "contexts": args.contexts,
        "estimate": estimate.to_dict(),
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
