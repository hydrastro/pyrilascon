from pathlib import Path
import json
import subprocess

from ascon_arch import (
    AeadBenchmarkShape,
    BenchmarkResult,
    PermutationProfile,
    TargetTechnology,
    aead128_cycle_estimate,
    permutation_config_for_profile,
    throughput_estimate,
)

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware" / "ascon_accel"


def test_aead128_cycle_estimates_reflect_rounds_per_cycle() -> None:
    shape = AeadBenchmarkShape(ad_bytes=32, text_bytes=1024)
    one_rpc = permutation_config_for_profile(PermutationProfile.ONE_ROUND_PER_CYCLE, TargetTechnology.FPGA)
    four_rpc = permutation_config_for_profile(PermutationProfile.FOUR_ROUNDS_PER_CYCLE, TargetTechnology.FPGA)
    eight_rpc = permutation_config_for_profile(PermutationProfile.EIGHT_ROUNDS_PER_CYCLE, TargetTechnology.FPGA)

    assert aead128_cycle_estimate(one_rpc, shape).sustained_block_interval_cycles == 8
    assert aead128_cycle_estimate(four_rpc, shape).sustained_block_interval_cycles == 2
    assert aead128_cycle_estimate(eight_rpc, shape).sustained_block_interval_cycles == 1


def test_throughput_estimate_increases_for_4rpc_and_8rpc() -> None:
    shape = AeadBenchmarkShape(ad_bytes=32, text_bytes=4096)
    one = throughput_estimate(
        permutation_config_for_profile(PermutationProfile.ONE_ROUND_PER_CYCLE, TargetTechnology.FPGA),
        shape,
        clock_mhz=27.0,
    )
    four = throughput_estimate(
        permutation_config_for_profile(PermutationProfile.FOUR_ROUNDS_PER_CYCLE, TargetTechnology.FPGA),
        shape,
        clock_mhz=27.0,
    )
    eight = throughput_estimate(
        permutation_config_for_profile(PermutationProfile.EIGHT_ROUNDS_PER_CYCLE, TargetTechnology.FPGA),
        shape,
        clock_mhz=27.0,
    )
    assert four.sustained_payload_mbps > one.sustained_payload_mbps
    assert eight.sustained_payload_mbps > four.sustained_payload_mbps


def test_benchmark_result_reports_speedup_gate() -> None:
    result = BenchmarkResult(
        design_name="demo",
        board="sim",
        algorithm="aead128",
        operation="encrypt",
        clock_mhz=27.0,
        ad_bytes=16,
        text_bytes=64,
        hardware_cycles=100,
        software_cycles=250,
    )
    payload = result.to_dict()
    assert payload["speedup_vs_software"] == 2.5
    assert payload["beats_software"] is True
    assert payload["hardware_throughput_mbps"] > 0.0


def test_estimate_throughput_tool_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "estimate.json"
    subprocess.run(
        [
            "python",
            "tools/estimate_throughput.py",
            "--permutation-profile",
            "eight_rounds_per_cycle",
            "--clock-mhz",
            "27",
            "--text-bytes",
            "1024",
            "--out",
            str(out),
        ],
        check=True,
        cwd=ROOT,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["permutation_profile"] == "eight_rounds_per_cycle"
    assert data["estimate"]["sustained_payload_mbps"] == 3456.0


def test_benchmark_documentation_exists() -> None:
    doc = ROOT / "docs" / "benchmark_methodology.md"
    text = doc.read_text(encoding="utf-8")
    assert "NEORV32 software Ascon" in text
    assert "speedup_vs_software > 1.0" in text
    assert "ascon_accel_benchmark.h" in text


def test_firmware_benchmark_helper_compiles(tmp_path: Path) -> None:
    obj = tmp_path / "ascon_accel_benchmark.o"
    subprocess.run(
        [
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FW),
            "-c",
            str(FW / "ascon_accel_benchmark.c"),
            "-o",
            str(obj),
        ],
        check=True,
        cwd=ROOT,
    )
    assert obj.exists()
