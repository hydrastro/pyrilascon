from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "run_neorv32_stream_board_session.py"
ROOT_MAKEFILE = ROOT / "Makefile"
BOARD_MAKEFILE = ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile"
DOC = ROOT / "docs" / "neorv32_stream_board_session.md"

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


def run_tool(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def make_package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    subprocess.run(
        [sys.executable, "tools/prepare_neorv32_stream_board_build.py", "--out", str(package), "--clean"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return package


def test_board_session_tool_generates_json_from_package(tmp_path: Path) -> None:
    package = make_package(tmp_path)

    completed = run_tool("--package", str(package), "--json")
    session = json.loads(completed.stdout)

    assert session["schema_version"] == 1
    assert session["name"] == "tangnano9k_neorv32_stream_axis_mmio_board_session"
    assert session["package_dir"] == str(package)
    assert session["memory_map"]["csr_base"] == "0xFFEB0000"
    assert session["memory_map"]["axis_mmio_base"] == "0xFFEB0100"
    assert session["firmware"]["mode"] == "USE_CFS_AXIS_MMIO=1"
    assert session["programming"]["requested"] is False
    assert session["checks"]["package_plan_ok"] is True
    assert session["session_ok"] is True


def test_board_session_tool_writes_default_reports(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    out_dir = ROOT / "build" / "neorv32_stream_axis_mmio" / "session"

    completed = run_tool("--package", str(package), "--write-defaults", "--check")

    assert completed.stdout.strip() == "ok"
    assert (out_dir / "session.json").exists()
    assert (out_dir / "session.md").exists()
    assert "# NEORV32 stream board session" in (out_dir / "session.md").read_text(encoding="utf-8")


def test_board_session_tool_embeds_uart_report(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    log = tmp_path / "uart.log"
    log.write_text(SAMPLE_PASS_LOG, encoding="utf-8")

    completed = run_tool("--package", str(package), "--uart-log", str(log), "--strict-uart", "--json")
    session = json.loads(completed.stdout)

    assert session["uart_report"]["headline"] == "pass"
    assert session["uart_report"]["hardware"]["axis_mmio"]["tx"] == 4
    assert session["checks"]["uart_report_passed_if_supplied"] is True


def test_board_session_tool_reports_missing_uart_log_cleanly(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    missing = tmp_path / "missing.log"

    completed = run_tool("--package", str(package), "--uart-log", str(missing), check=False)

    assert completed.returncode == 2
    assert "UART log file does not exist" in completed.stderr
    assert "Traceback" not in completed.stderr


def test_board_session_tool_requires_bitstream_when_programming(tmp_path: Path) -> None:
    package = make_package(tmp_path)

    completed = run_tool("--package", str(package), "--program", check=False)

    assert completed.returncode == 2
    assert "--program requires --bitstream" in completed.stderr
    assert "Traceback" not in completed.stderr


def test_board_session_markdown_contains_board_steps(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    out = tmp_path / "session.md"

    run_tool("--package", str(package), "--markdown", "--out", str(out))

    markdown = out.read_text(encoding="utf-8")
    assert "# NEORV32 stream board session" in markdown
    assert "AXI-stream MMIO base" in markdown
    assert "USE_CFS_AXIS_MMIO=1" in markdown
    assert "openFPGALoader" in markdown


def test_makefiles_and_docs_expose_board_session_target() -> None:
    root_makefile = ROOT_MAKEFILE.read_text(encoding="utf-8")
    board_makefile = BOARD_MAKEFILE.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "neorv32-stream-board-session:" not in root_makefile
    assert "session:" in board_makefile
    assert "run_neorv32_stream_board_session.py" in board_makefile
    assert "make -C boards/tangnano9k/neorv32_stream_axis_mmio session" in doc
    assert "session.json" in doc
