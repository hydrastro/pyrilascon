from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.parse_sweep_log import SweepLogError, parse_log, render_markdown

ROOT = Path(__file__).resolve().parents[1]

SAMPLE = """
\ufffd\ufffdpyrilascon NEORV32 ASCON benchmark
BUILD        : tangnano20k-neorv32-mmio
MAX_BYTES    : 32
SWEEP_CASES  : 1
CASE name=empty ad=0 pt=0 sw_enc_cy=0:34643 sw_dec_cy=0:34949 hw_enc_cy=0:31 hw_dec_cy=0:31 hw_enc_e2e_cy=0:4423 hw_dec_e2e_cy=0:4475 enc_ok=1 dec_ok=1 tag_valid=1 hw_enc_err=0x0 hw_dec_err=0x0\ufffd
AUTH_NEGATIVE enc_status=0 dec_status=-3 tag_valid=0 hw_err=0x4 output_unchanged=1 pass=1
SUMMARY      : passed=1 failed=0 total=1 negative_pass=1
PASS
"""


def test_parse_complete_sweep_distinguishes_e2e_and_core_speedup() -> None:
    report = parse_log(SAMPLE, strict=True)
    case = report.cases[0]

    assert report.overall_pass is True
    assert case.enc_e2e_speedup == pytest.approx(34643 / 4423)
    assert case.dec_e2e_speedup == pytest.approx(34949 / 4475)
    assert case.enc_core_speedup == pytest.approx(34643 / 31)
    assert report.negative is not None and report.negative.passed
    markdown = render_markdown(report)
    assert "Primary metric: end-to-end speedup" in markdown
    assert "7.83×" in markdown


def test_strict_parser_rejects_truncated_capture() -> None:
    with pytest.raises(SweepLogError, match="expected 1 CASE records|missing SUMMARY|missing final PASS"):
        parse_log("SWEEP_CASES  : 1\n", strict=True)


def test_parser_cli_writes_strict_json(tmp_path: Path) -> None:
    log = tmp_path / "uart.log"
    out = tmp_path / "report.json"
    log.write_text(SAMPLE, encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "tools/parse_sweep_log.py",
            str(log),
            "--strict",
            "--json",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["overall_pass"] is True
    assert data["cases"][0]["enc_e2e_speedup"] == pytest.approx(34643 / 4423)
