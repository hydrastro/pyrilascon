from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware" / "ascon_accel"


def test_firmware_driver_is_split_into_control_and_data_planes() -> None:
    expected = {
        "ascon_accel.c",
        "ascon_accel_control.c",
        "ascon_accel_caps.c",
        "ascon_accel_mmio_data.c",
        "ascon_accel_axis_data.c",
        "ascon_accel_internal.h",
    }
    assert expected.issubset({path.name for path in FW.iterdir()})
    public_header = (FW / "ascon_accel.h").read_text(encoding="utf-8")
    high_level = (FW / "ascon_accel.c").read_text(encoding="utf-8")
    assert "ascon_accel_data_plane_t" in public_header
    assert "ASCON_ACCEL_DATA_PLANE_MMIO_WORD" in public_header
    assert "ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL" in public_header
    assert "ascon_accel_set_data_plane" in public_header
    assert "send_payload" in high_level
    assert "recv_payload" in high_level
    assert "ascon_accel_mmio_stream_bytes" in high_level
    assert "ascon_accel_axis_stream_bytes" in high_level


def test_neorv32_demo_makefile_builds_all_driver_translation_units() -> None:
    makefile = (ROOT / "firmware" / "neorv32_ascon_demo" / "Makefile").read_text(encoding="utf-8")
    for name in (
        "ascon_accel.c",
        "ascon_accel_control.c",
        "ascon_accel_caps.c",
        "ascon_accel_mmio_data.c",
        "ascon_accel_axis_data.c",
    ):
        assert name in makefile


def test_host_c_driver_files_compile(tmp_path: Path) -> None:
    objects = []
    for source in (
        "ascon_accel.c",
        "ascon_accel_control.c",
        "ascon_accel_caps.c",
        "ascon_accel_mmio_data.c",
        "ascon_accel_axis_data.c",
        "ascon_accel_axis_mock_transport.c",
        "main_demo.c",
    ):
        obj = tmp_path / f"{source}.o"
        subprocess.run(
            ["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(FW), "-c", str(FW / source), "-o", str(obj)],
            check=True,
            cwd=ROOT,
        )
        objects.append(obj)
    assert all(obj.exists() for obj in objects)
