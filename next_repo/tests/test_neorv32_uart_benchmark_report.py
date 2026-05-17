from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.parse_neorv32_ascon_uart_log import UartBenchmarkParseError, parse_uart_log, render_markdown

REPO_ROOT = Path(__file__).resolve().parents[1]

SAMPLE_PASS_LOG = """
pyrilascon NEORV32 ASCON benchmark
DATA PLANE   : AXI_STREAM_MMIO
AXIS BASE    : 0xffeb0100
ABI          : 0x00010000
CAPS         : 0x00000001
SW CT        : 00112233445566778899aabbccddeeff
SW TAG       : 0123456789abcdeffedcba9876543210
HW CT        : 00112233445566778899aabbccddeeff
HW TAG       : 0123456789abcdeffedcba9876543210
HW PT        : 202122232425262728292a2b2c2d2e2f
ENC status       : 0
ENC hw cycles    : 0:100
ENC hw mcy/byte  : 6
ENC tag valid    : 1
ENC hw err       : 0x0
DEC status       : 0
DEC hw cycles    : 0:120
DEC hw mcy/byte  : 7
DEC tag valid    : 1
DEC hw err       : 0x0
AXIS TX beats : 4
AXIS RX beats : 4
AXIS status   : 0
SW cycles    : 0:1000
ENC speedup x1000: 10000
DEC speedup x1000: 8333
PASS
"""

SAMPLE_WARN_LOG = SAMPLE_PASS_LOG.replace("PASS\n", "WARN: hardware encryption did not beat software for this shape\nPASS\n")
SAMPLE_FAIL_LOG = SAMPLE_PASS_LOG.replace("HW TAG       : 0123456789abcdeffedcba9876543210", "HW TAG       : ffffffffffffffffffffffffffffffff").replace("PASS", "FAIL: encryption mismatch")


def test_parse_neorv32_uart_log_extracts_benchmark_fields() -> None:
    report = parse_uart_log(SAMPLE_PASS_LOG, strict=True)

    assert report["headline"] == "pass"
    assert report["data_plane"] == "AXI_STREAM_MMIO"
    assert report["axis_base"] == "0xffeb0100"
    assert report["software"]["cycles"] == 1000
    assert report["hardware"]["encryption"]["cycles"] == 100
    assert report["hardware"]["decryption"]["cycles"] == 120
    assert report["hardware"]["encryption"]["speedup"] == 10.0
    assert report["hardware"]["axis_mmio"]["tx"] == 4
    assert report["checks"]["encryption_matches_reference"] is True
    assert report["checks"]["hardware_encrypt_beats_software"] is True
    assert report["checks"]["hardware_decrypt_beats_software"] is True


def test_parse_neorv32_uart_log_records_warnings_without_failing() -> None:
    report = parse_uart_log(SAMPLE_WARN_LOG, strict=True)

    assert report["headline"] == "pass"
    assert report["warnings"] == ["WARN: hardware encryption did not beat software for this shape"]


def test_parse_neorv32_uart_log_strict_mode_rejects_failures() -> None:
    with pytest.raises(UartBenchmarkParseError):
        parse_uart_log(SAMPLE_FAIL_LOG, strict=True)

    report = parse_uart_log(SAMPLE_FAIL_LOG, strict=False)
    assert report["headline"] == "fail"
    assert report["checks"]["encryption_matches_reference"] is False
    assert report["failures"] == ["FAIL: encryption mismatch"]


def test_render_neorv32_uart_report_markdown_contains_summary() -> None:
    report = parse_uart_log(SAMPLE_PASS_LOG, strict=True)
    markdown = render_markdown(report)

    assert "# NEORV32 ASCON benchmark report" in markdown
    assert "| Data plane | AXI_STREAM_MMIO |" in markdown
    assert "| ENC HW cycles | 100 |" in markdown
    assert "`encryption_matches_reference`" in markdown


def test_parse_neorv32_uart_log_cli_json(tmp_path: Path) -> None:
    log = tmp_path / "uart.log"
    log.write_text(SAMPLE_PASS_LOG, encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "tools/parse_neorv32_ascon_uart_log.py", str(log), "--json", "--strict"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)
    assert report["headline"] == "pass"
    assert report["hardware"]["axis_mmio"]["rx"] == 4


def test_parse_neorv32_uart_log_cli_markdown_out(tmp_path: Path) -> None:
    log = tmp_path / "uart.log"
    out = tmp_path / "report.md"
    log.write_text(SAMPLE_PASS_LOG, encoding="utf-8")

    subprocess.run(
        [sys.executable, "tools/parse_neorv32_ascon_uart_log.py", str(log), "--markdown", "--strict", "--out", str(out)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert out.exists()
    assert "| Result | pass |" in out.read_text(encoding="utf-8")


def test_parse_neorv32_uart_log_has_direct_execution_imports() -> None:
    source = (REPO_ROOT / "tools" / "parse_neorv32_ascon_uart_log.py").read_text(encoding="utf-8")
    assert "from dataclasses import dataclass" in source
    assert "raise SystemExit(main())" in source


def test_parse_neorv32_uart_log_cli_missing_file_reports_clean_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing_uart.log"
    completed = subprocess.run(
        [sys.executable, "tools/parse_neorv32_ascon_uart_log.py", str(missing), "--strict", "--markdown"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "UART log file does not exist" in completed.stderr
    assert "Traceback" not in completed.stderr
