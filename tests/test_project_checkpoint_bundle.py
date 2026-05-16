from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT / "tools"))
from generate_project_checkpoint_bundle import build_checkpoint, validate_checkpoint  # noqa: E402


def test_checkpoint_bundle_generates_metadata_and_archive(tmp_path: Path) -> None:
    out_dir = tmp_path / "checkpoint"
    zip_out = tmp_path / "checkpoint.zip"

    metadata = build_checkpoint(out_dir, zip_out, clean=True)

    assert metadata["project_status"] == "ready_for_real_board_integration"
    assert metadata["milestones_complete"] == metadata["milestones_total"]
    assert metadata["memory_map"]["csr_base"] == "0xFFEB0000"
    assert metadata["memory_map"]["axis_mmio_base"] == "0xFFEB0100"
    assert zip_out.exists()
    validate_checkpoint(out_dir, zip_out)


def test_checkpoint_bundle_contains_status_manifest_and_evidence(tmp_path: Path) -> None:
    out_dir = tmp_path / "checkpoint"
    zip_out = tmp_path / "checkpoint.zip"
    build_checkpoint(out_dir, zip_out, clean=True)

    assert (out_dir / "checkpoint.md").read_text(encoding="utf-8").startswith("# pyrilascon project checkpoint bundle")
    assert (out_dir / "project_status.json").exists()
    assert (out_dir / "board_manifest.json").exists()
    assert (out_dir / "files" / "rtl" / "stream" / "ascon_aead128_stream.v").exists()
    assert (out_dir / "files" / "firmware" / "ascon_accel" / "ascon_accel_axis_ref_emulator.c").exists()
    assert (out_dir / "files" / "tests" / "test_stream_axis_mmio_system_sim.py").exists()


def test_checkpoint_zip_has_expected_members(tmp_path: Path) -> None:
    out_dir = tmp_path / "checkpoint"
    zip_out = tmp_path / "checkpoint.zip"
    build_checkpoint(out_dir, zip_out, clean=True)

    with zipfile.ZipFile(zip_out) as zf:
        names = set(zf.namelist())

    assert "checkpoint.json" in names
    assert "checkpoint.md" in names
    assert "project_status.json" in names
    assert "board_manifest.json" in names
    assert "files/README.md" in names
    assert "files/boards/tangnano9k/neorv32_stream_axis_mmio/manifest.json" in names


def test_checkpoint_cli_write_defaults_json_and_check(tmp_path: Path) -> None:
    out_dir = tmp_path / "checkpoint"
    zip_out = tmp_path / "checkpoint.zip"

    generated = subprocess.run(
        [
            sys.executable,
            "tools/generate_project_checkpoint_bundle.py",
            "--write-defaults",
            "--clean",
            "--out-dir",
            str(out_dir),
            "--zip-out",
            str(zip_out),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(generated.stdout)
    assert payload["name"] == "pyrilascon_project_checkpoint_bundle"

    checked = subprocess.run(
        [
            sys.executable,
            "tools/generate_project_checkpoint_bundle.py",
            "--check",
            "--out-dir",
            str(out_dir),
            "--zip-out",
            str(zip_out),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert checked.stdout.strip() == "ok"


def test_checkpoint_makefile_target_is_exposed() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "project-checkpoint-bundle" in makefile
    assert "generate_project_checkpoint_bundle.py --write-defaults --clean" in makefile
    assert "generate_project_checkpoint_bundle.py --check" in makefile


def test_checkpoint_documentation_exists() -> None:
    doc = (REPO_ROOT / "docs" / "project_checkpoint_bundle.md").read_text(encoding="utf-8")

    assert "make project-checkpoint-bundle" in doc
    assert "build/project_checkpoint_bundle.zip" in doc
    assert "real Tang Nano/NEORV32 build" in doc


def test_readme_mentions_checkpoint_bundle() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Project checkpoint bundle" in readme
    assert "make project-checkpoint-bundle" in readme
    assert "build/project_checkpoint_bundle.zip" in readme
