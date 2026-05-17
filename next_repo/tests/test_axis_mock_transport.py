from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware" / "ascon_accel"


def test_axis_mock_transport_files_exist() -> None:
    assert (FW / "ascon_accel_axis_mock_transport.h").is_file()
    assert (FW / "ascon_accel_axis_mock_transport.c").is_file()


def test_axis_mock_transport_documentation_exists() -> None:
    doc = ROOT / "docs" / "axis_transport_mocking.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "ascon_accel_axis_transport_t" in text
    assert "ASCON_ACCEL_ERR_TRANSPORT" in text
    assert "AD, text, and customization streams" in text


def test_axis_mock_transport_compiles_and_runs(tmp_path: Path) -> None:
    program = tmp_path / "test_axis_mock_transport.c"
    program.write_text(
        r'''
#include <stdint.h>
#include <string.h>
#include "ascon_accel_axis_mock_transport.h"

int main(void) {
  ascon_accel_axis_mock_transport_ctx_t ctx;
  ascon_accel_axis_mock_init(&ctx);
  ascon_accel_axis_transport_t transport = ascon_accel_axis_mock_transport(&ctx);

  const uint8_t ad[] = {0xA0, 0xA1, 0xA2};
  const uint8_t text[] = {0x10, 0x11, 0x12, 0x13};
  const uint8_t custom[] = {0xC0};
  const uint8_t rx[] = {0x55, 0x66, 0x77};
  uint8_t out[3] = {0};

  if (transport.send(transport.ctx, ad, sizeof(ad), ASCON_ACCEL_STREAM_AD) != ASCON_ACCEL_OK) return 1;
  if (transport.send(transport.ctx, text, sizeof(text), ASCON_ACCEL_STREAM_TEXT) != ASCON_ACCEL_OK) return 2;
  if (transport.send(transport.ctx, custom, sizeof(custom), ASCON_ACCEL_STREAM_CUSTOM) != ASCON_ACCEL_OK) return 3;
  if (ascon_accel_axis_mock_load_rx(&ctx, rx, sizeof(rx)) != ASCON_ACCEL_OK) return 4;
  if (transport.recv(transport.ctx, out, sizeof(out)) != ASCON_ACCEL_OK) return 5;

  if (ctx.ad_len != sizeof(ad) || memcmp(ctx.ad, ad, sizeof(ad)) != 0) return 6;
  if (ctx.text_len != sizeof(text) || memcmp(ctx.text, text, sizeof(text)) != 0) return 7;
  if (ctx.custom_len != sizeof(custom) || memcmp(ctx.custom, custom, sizeof(custom)) != 0) return 8;
  if (memcmp(out, rx, sizeof(rx)) != 0) return 9;
  if (ctx.send_calls != 3u || ctx.recv_calls != 1u) return 10;

  if (transport.recv(transport.ctx, out, 1u) != ASCON_ACCEL_ERR_TRANSPORT) return 11;
  return 0;
}
''',
        encoding="utf-8",
    )
    exe = tmp_path / "test_axis_mock_transport"
    subprocess.run(
        [
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FW),
            str(program),
            str(FW / "ascon_accel_axis_mock_transport.c"),
            "-o",
            str(exe),
        ],
        check=True,
        cwd=ROOT,
    )
    subprocess.run([str(exe)], check=True, cwd=ROOT)
