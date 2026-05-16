from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT / "tools"))
from generate_project_status_report import generate_report, render_markdown, validate_report  # noqa: E402


def test_project_status_report_all_declared_milestones_have_evidence() -> None:
    report = generate_report(REPO_ROOT)

    assert report["status"] == "ready_for_real_board_integration"
    assert report["complete_milestones"] == report["milestone_count"]
    assert validate_report(report) == []


def test_project_status_report_captures_remaining_real_board_gate() -> None:
    report = generate_report(REPO_ROOT)

    assert report["next_gate"] == "real Tang Nano / NEORV32 build plus UART benchmark report"
    remaining = "\n".join(item["item"] + " " + item["detail"] for item in report["remaining_work"])
    assert "Real Tang Nano / NEORV32 build" in remaining
    assert "UART" in remaining
    assert "DMA" in remaining
    assert "High-throughput FPGA" in remaining


def test_project_status_report_includes_stream_and_board_milestones() -> None:
    report = generate_report(REPO_ROOT)
    milestones = {item["key"]: item for item in report["milestones"]}

    assert milestones["stream_encrypt_backend"]["status"] == "complete"
    assert milestones["buffered_decrypt_backend"]["status"] == "complete"
    assert milestones["full_axis_mmio_system_sim"]["status"] == "complete"
    assert milestones["neorv32_cfs_wrapper"]["status"] == "complete"
    assert milestones["board_handoff"]["status"] == "complete"


def test_project_status_markdown_mentions_limitations_and_next_gate() -> None:
    markdown = render_markdown(generate_report(REPO_ROOT))

    assert "# ASCON project status report" in markdown
    assert "ready_for_real_board_integration" in markdown
    assert "Buffered decrypt is bounded" in markdown
    assert "real Tang Nano / NEORV32 build plus UART benchmark report" in markdown


def test_project_status_cli_check_json_and_markdown(tmp_path: Path) -> None:
    json_out = tmp_path / "status.json"
    md_out = tmp_path / "status.md"

    check = subprocess.run(
        [sys.executable, "tools/generate_project_status_report.py", "--check"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert check.stdout.strip() == "ok"

    subprocess.run(
        [
            sys.executable,
            "tools/generate_project_status_report.py",
            "--write-defaults",
            "--out-json",
            str(json_out),
            "--out-md",
            str(md_out),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["project"] == "pyrilascon ASCON FPGA/ASIC generator"
    assert md_out.read_text(encoding="utf-8").startswith("# ASCON project status report")


def test_project_status_report_makefile_target_is_exposed() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "project-status-report" in makefile
    assert "generate_project_status_report.py --check" in makefile
    assert "generate_project_status_report.py --write-defaults" in makefile


def test_project_status_report_documentation_exists() -> None:
    doc = (REPO_ROOT / "docs" / "project_status_report.md").read_text(encoding="utf-8")

    assert "make project-status-report" in doc
    assert "real Tang Nano / NEORV32 build" in doc
