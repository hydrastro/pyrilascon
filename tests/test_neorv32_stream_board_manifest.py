import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "manifest.json"
BOARD_README = ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "README.md"
BOARD_MAKEFILE = ROOT / "boards" / "tangnano9k" / "neorv32_stream_axis_mmio" / "Makefile"
DOC = ROOT / "docs" / "neorv32_stream_board_manifest.md"
TOOL = ROOT / "tools" / "print_neorv32_stream_board_manifest.py"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_tangnano9k_neorv32_stream_manifest_exists_and_names_board_target() -> None:
    manifest = load_manifest()
    assert manifest["schema_version"] == 1
    assert manifest["name"] == "tangnano9k_neorv32_stream_axis_mmio"
    assert manifest["board"]["name"] == "Tang Nano 9K"
    assert manifest["board"]["status"] == "bringup_scaffold"
    assert "stream-native ASCON AEAD128" in manifest["description"]


def test_manifest_freezes_single_cfs_stream_memory_map() -> None:
    memory = load_manifest()["memory_map"]
    assert memory["ascon_cfs_base"] == "0xFFEB0000"
    assert memory["csr_window"]["base"] == "0xFFEB0000"
    assert memory["csr_window"]["offset"] == "0x000"
    assert memory["csr_window"]["size_bytes"] == 256
    assert memory["axis_mmio_window"]["base"] == "0xFFEB0100"
    assert memory["axis_mmio_window"]["offset"] == "0x100"
    assert memory["axis_mmio_window"]["size_bytes"] == 256


def test_manifest_references_existing_rtl_and_firmware_assets() -> None:
    manifest = load_manifest()
    paths = [
        manifest["top"]["cfs_wrapper"],
        manifest["top"]["accelerator_system"],
        manifest["rtl"]["primary_file_list"],
        manifest["firmware"]["directory"],
        *manifest["rtl"]["required_sources"],
    ]
    for relpath in paths:
        assert (ROOT / relpath).exists(), relpath


def test_manifest_rtl_source_list_matches_cfs_file_list_order() -> None:
    manifest = load_manifest()
    manifest_sources = manifest["rtl"]["required_sources"]
    file_list = ROOT / manifest["rtl"]["primary_file_list"]
    file_list_sources = [
        line.strip()
        for line in file_list.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert manifest_sources == file_list_sources
    assert manifest_sources[-1] == "rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd"


def test_manifest_firmware_mode_selects_cfs_axis_mmio_addresses() -> None:
    firmware = load_manifest()["firmware"]
    assert firmware["make_mode"] == "USE_CFS_AXIS_MMIO=1"
    assert "boards/tangnano9k/neorv32_stream_axis_mmio" in firmware["command"]
    assert "firmware" in firmware["command"]
    assert firmware["defines"]["ASCON_BENCH_USE_AXIS_MMIO"] == "1"
    assert firmware["defines"]["ASCON_ACCEL_BASE_ADDR"] == "0xFFEB0000u"
    assert firmware["defines"]["ASCON_ACCEL_AXIS_MMIO_BASE_ADDR"] == "0xFFEB0100u"


def test_manifest_tool_validates_and_prints_summary() -> None:
    check = subprocess.run(
        [sys.executable, str(TOOL), "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert check.stdout.strip() == "ok"

    summary = subprocess.run(
        [sys.executable, str(TOOL)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "tangnano9k_neorv32_stream_axis_mmio" in summary
    assert "0xFFEB0000" in summary
    assert "0xFFEB0100" in summary
    assert "USE_CFS_AXIS_MMIO=1" in summary


def test_board_makefile_and_docs_expose_bringup_contract() -> None:
    makefile = BOARD_MAKEFILE.read_text(encoding="utf-8")
    readme = BOARD_README.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "make manifest" in readme
    assert "make check" in readme
    assert "USE_CFS_AXIS_MMIO=1" in readme
    assert "0xFFEB0100" in readme
    assert "tools/print_neorv32_stream_board_manifest.py --check" in doc
    assert "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR = 0xFFEB0100u" in doc
    assert "firmware:" in makefile
    assert "USE_CFS_AXIS_MMIO=1 clean_all exe" in makefile
