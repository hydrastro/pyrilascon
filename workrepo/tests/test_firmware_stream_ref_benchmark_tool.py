from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_firmware_stream_ref_benchmark_tool_runs_and_reports_cases() -> None:
    completed = subprocess.run(
        [
            "python",
            "tools/run_firmware_stream_ref_benchmark.py",
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)
    assert report["backend"] == "axis_stream_ref_emulator"
    assert report["case_count"] == 4
    assert report["all_passed"] is True
    names = {case["name"] for case in report["cases"]}
    assert names == {"empty", "short", "partial", "two_block"}
    for case in report["cases"]:
        assert case["enc_ok"] == 1
        assert case["dec_ok"] == 1
        assert case["suppressed"] == 1
        assert case["invalid_status"] == -3
        assert case["enc_cycles"] > 0
        assert case["dec_cycles"] > 0


def test_firmware_stream_ref_benchmark_has_make_target_and_documents_axis_path() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "firmware-stream-ref-bench" in makefile
    assert "tools/run_firmware_stream_ref_benchmark.py --json" in makefile

    doc = (ROOT / "docs" / "firmware_stream_ref_benchmark.md").read_text(encoding="utf-8")
    assert "AXI-stream reference emulator" in doc
    assert "invalid decrypt tag" in doc
    assert "NEORV32" in doc


def test_axis_ref_emulator_cycle_counter_is_monotonic_for_benchmarks() -> None:
    header = (ROOT / "firmware" / "ascon_accel" / "ascon_accel_axis_ref_emulator.h").read_text(encoding="utf-8")
    source = (ROOT / "firmware" / "ascon_accel" / "ascon_accel_axis_ref_emulator.c").read_text(encoding="utf-8")
    assert "uint64_t cycle_counter" in header
    assert "ctx->cycle_counter += 48u" in source
    assert "set_cycle_count(ctx, ctx->cycle_counter)" in source
