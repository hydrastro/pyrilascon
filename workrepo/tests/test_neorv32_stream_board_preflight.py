import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "neorv32_stream_board_preflight.py"
ROOT_MAKEFILE = ROOT / "Makefile"
BOARD_MAKEFILE = ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile"
DOC = ROOT / "docs" / "neorv32_stream_board_preflight.md"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_preflight_tool_check_passes() -> None:
    result = run_tool("--check")
    assert result.stdout.strip() == "ok"


def test_preflight_json_records_memory_map_firmware_and_sources() -> None:
    result = run_tool("--json")
    plan = json.loads(result.stdout)

    assert plan["schema_version"] == 1
    assert plan["name"] == "tangnano9k_neorv32_stream_axis_mmio_preflight"
    assert plan["memory_map"]["csr_base"] == "0xFFEB0000"
    assert plan["memory_map"]["axis_mmio_base"] == "0xFFEB0100"
    assert plan["firmware"]["make_mode"] == "USE_CFS_AXIS_MMIO=1"
    assert plan["rtl"]["primary_file_list"] == "rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f"
    assert plan["rtl"]["sources"][-1] == "rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd"


def test_preflight_json_records_root_and_board_targets() -> None:
    plan = json.loads(run_tool("--json").stdout)
    root_targets = plan["targets"]["root_makefile"]
    board_targets = plan["targets"]["board_makefile"]

    assert root_targets["neorv32-stream-board-manifest"] is True
    assert root_targets["neorv32-stream-board-preflight"] is True
    assert root_targets["stream-axis-mmio-system-sim"] is True
    assert board_targets["manifest"] is True
    assert board_targets["check"] is True
    assert board_targets["preflight"] is True
    assert board_targets["firmware"] is True


def test_preflight_writes_build_json(tmp_path: Path) -> None:
    out = tmp_path / "preflight.json"
    result = run_tool("--out", str(out))
    assert "pre-board commands" in result.stdout
    plan = json.loads(out.read_text(encoding="utf-8"))
    assert plan["pre_board_commands"][0] == "make neorv32-stream-board-manifest"
    assert "make neorv32-stream-board-preflight" in plan["pre_board_commands"]


def test_preflight_reports_optional_neorv32_home(tmp_path: Path) -> None:
    fake_home = tmp_path / "neorv32"
    (fake_home / "sw" / "common").mkdir(parents=True)
    (fake_home / "sw" / "common" / "common.mk").write_text("# fake\n", encoding="utf-8")

    plan = json.loads(run_tool("--neorv32-home", str(fake_home), "--json").stdout)
    assert plan["neorv32_home"]["provided"] is True
    assert plan["neorv32_home"]["ready_for_firmware_build"] is True


def test_preflight_require_neorv32_home_fails_when_missing(tmp_path: Path) -> None:
    missing_home = tmp_path / "missing"
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--neorv32-home",
            str(missing_home),
            "--require-neorv32-home",
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "NEORV32_HOME" in result.stderr or "NEORV32_HOME" in result.stdout


def test_makefiles_and_docs_expose_preflight_target() -> None:
    root_makefile = ROOT_MAKEFILE.read_text(encoding="utf-8")
    board_makefile = BOARD_MAKEFILE.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "neorv32-stream-board-preflight:" in root_makefile
    assert "tools/neorv32_stream_board_preflight.py --check" in root_makefile
    assert "preflight:" in board_makefile
    assert "tools/neorv32_stream_board_preflight.py --out" in board_makefile
    assert "make neorv32-stream-board-preflight" in doc
    assert "build/neorv32_stream_axis_mmio/preflight.json" in doc
