import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "plan_neorv32_stream_board_build.py"
ROOT_MAKEFILE = ROOT / "Makefile"
BOARD_MAKEFILE = ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile"
DOC = ROOT / "docs" / "neorv32_stream_board_build_plan.md"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_board_build_plan_tool_generates_json_from_package(tmp_path: Path) -> None:
    package = tmp_path / "package"
    subprocess.run(
        [sys.executable, "tools/prepare_neorv32_stream_board_build.py", "--out", str(package), "--clean"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    completed = run_tool("--package", str(package), "--json")
    plan = json.loads(completed.stdout)

    assert plan["schema_version"] == 1
    assert plan["name"] == "tangnano9k_neorv32_stream_axis_mmio_build_plan"
    assert plan["dry_run_ok"] is True
    assert plan["memory_map"]["csr_base"] == "0xFFEB0000"
    assert plan["memory_map"]["axis_mmio_base"] == "0xFFEB0100"
    assert plan["firmware"]["mode"] == "USE_CFS_AXIS_MMIO=1"
    assert plan["rtl"]["verilog_count"] > 0
    assert plan["rtl"]["vhdl_count"] == 1
    assert plan["checks"]["all_sources_exist"] is True


def test_board_build_plan_tool_writes_default_reports(tmp_path: Path) -> None:
    package = tmp_path / "package"
    out_json = tmp_path / "build_plan.json"
    out_md = tmp_path / "build_plan.md"
    subprocess.run(
        [sys.executable, "tools/prepare_neorv32_stream_board_build.py", "--out", str(package), "--clean"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    run_tool("--package", str(package), "--json", "--out", str(out_json))
    run_tool("--package", str(package), "--markdown", "--out", str(out_md))

    assert json.loads(out_json.read_text(encoding="utf-8"))["dry_run_ok"] is True
    markdown = out_md.read_text(encoding="utf-8")
    assert "# NEORV32 stream board dry-run build plan" in markdown
    assert "CSR/MMIO base" in markdown
    assert "USE_CFS_AXIS_MMIO=1" in markdown


def test_board_build_plan_check_prints_ok(tmp_path: Path) -> None:
    package = tmp_path / "package"
    completed = run_tool("--package", str(package), "--ensure-package", "--check")
    assert completed.stdout.strip() == "ok"
    assert (package / "package.json").exists()


def test_board_build_plan_records_expected_stage_names(tmp_path: Path) -> None:
    package = tmp_path / "package"
    run_tool("--package", str(package), "--ensure-package", "--json", "--out", str(tmp_path / "plan.json"))
    plan = json.loads((tmp_path / "plan.json").read_text(encoding="utf-8"))
    stage_names = [stage["name"] for stage in plan["stages"]]

    assert stage_names == [
        "pre_board_validation",
        "firmware_build",
        "rtl_integration",
        "gowin_board_build",
        "uart_report",
    ]


def test_makefiles_and_docs_expose_board_build_plan_target() -> None:
    root_makefile = ROOT_MAKEFILE.read_text(encoding="utf-8")
    board_makefile = BOARD_MAKEFILE.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "neorv32-stream-board-build-plan:" not in root_makefile
    assert "build-plan:" in board_makefile
    assert "plan_neorv32_stream_board_build.py" in board_makefile
    assert "make -C boards/tangnano9k/neorv32_stream_axis_mmio build-plan" in doc
    assert "build_plan.json" in doc
