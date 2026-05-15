from tools.list_valid_configs import enumerate_selected_configs
from ascon_arch.enums import TargetTechnology


def test_selected_asic_config_listing_count() -> None:
    entries = enumerate_selected_configs(target=TargetTechnology.ASIC)
    assert len(entries) == 44
    assert all(entry.valid for entry in entries)


def test_selected_fpga_config_listing_count() -> None:
    entries = enumerate_selected_configs(target=TargetTechnology.FPGA)
    assert len(entries) == 26
    assert all(entry.valid for entry in entries)


def test_selected_config_listing_with_invalids() -> None:
    asic = enumerate_selected_configs(target=TargetTechnology.ASIC, include_invalid=True)
    fpga = enumerate_selected_configs(target=TargetTechnology.FPGA, include_invalid=True)
    assert sum(entry.valid for entry in asic) == 44
    assert len(asic) == 48
    assert sum(entry.valid for entry in fpga) == 26
    assert len(fpga) == 54


def test_list_valid_configs_cli_accepts_makefile_algorithm_option(tmp_path) -> None:
    import subprocess
    import sys

    out = tmp_path / "configs.txt"
    result = subprocess.run(
        [
            sys.executable,
            "tools/list_valid_configs.py",
            "--target",
            "both",
            "--algorithms",
            "requested",
            "--format",
            "text",
            "--out",
            str(out),
        ],
        check=True,
        cwd=".",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("valid=70")
