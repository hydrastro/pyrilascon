from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware" / "ascon_accel"


def test_public_header_exposes_axis_transport_callbacks() -> None:
    header = (FW / "ascon_accel.h").read_text(encoding="utf-8")
    assert "ascon_accel_axis_transport_t" in header
    assert "ascon_accel_stream_kind_t" in header
    assert "ASCON_ACCEL_ERR_TRANSPORT" in header
    assert "ascon_accel_set_axis_transport" in header
    assert "ascon_accel_axis_transport_configured" in header


def test_axis_data_plane_uses_capability_and_transport_callbacks() -> None:
    source = (FW / "ascon_accel_axis_data.c").read_text(encoding="utf-8")
    assert "ASCON_CAP_AXI_STREAM_DATA" in source
    assert "ASCON_ACCEL_ERR_TRANSPORT" in source
    assert "dev->axis_transport.send" in source
    assert "dev->axis_transport.recv" in source
    assert "ascon_accel_set_axis_transport" in source


def test_firmware_architecture_documentation_exists() -> None:
    doc = (ROOT / "docs" / "firmware_driver_architecture.md")
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "control plane" in text
    assert "data plane" in text
    assert "ascon_accel_axis_transport_t" in text
    assert "ASCON_CAP_AXI_STREAM_DATA" in text
    assert "ASCON_ACCEL_ERR_TRANSPORT" in text


def test_axis_transport_example_compiles(tmp_path: Path) -> None:
    example = tmp_path / "axis_transport_example.c"
    example.write_text(
        r'''
#include <stddef.h>
#include <stdint.h>
#include "ascon_accel.h"

static ascon_accel_status_t send_cb(
    void *ctx,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t kind) {
  (void)ctx;
  (void)data;
  (void)len;
  (void)kind;
  return ASCON_ACCEL_OK;
}

static ascon_accel_status_t recv_cb(void *ctx, uint8_t *data, size_t len) {
  (void)ctx;
  (void)data;
  (void)len;
  return ASCON_ACCEL_OK;
}

void configure_transport(ascon_accel_t *dev, void *ctx) {
  ascon_accel_axis_transport_t transport = {
    .ctx = ctx,
    .send = send_cb,
    .recv = recv_cb,
  };
  ascon_accel_set_axis_transport(dev, &transport);
  ascon_accel_set_data_plane(dev, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL);
}
''',
        encoding="utf-8",
    )
    obj = tmp_path / "axis_transport_example.o"
    subprocess.run(
        ["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(FW), "-c", str(example), "-o", str(obj)],
        check=True,
        cwd=ROOT,
    )
    assert obj.exists()
