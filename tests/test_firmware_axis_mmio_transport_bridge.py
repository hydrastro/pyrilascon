from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware" / "ascon_accel"


def compile_and_run(tmp_path: Path, source: str) -> None:
    program = tmp_path / "axis_mmio_transport_test.c"
    binary = tmp_path / "axis_mmio_transport_test"
    program.write_text(source, encoding="utf-8")
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
            str(FW / "ascon_accel_axis_mmio_transport.c"),
            "-o",
            str(binary),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([str(binary)], cwd=ROOT, check=True)


def test_axis_mmio_transport_packs_stream_beats_for_cpu_driven_bridge(tmp_path: Path) -> None:
    compile_and_run(
        tmp_path,
        r'''
#include <stdint.h>
#include "ascon_accel_axis_mmio_transport.h"

#define WORD(off) regs[(off) / 4u]

int main(void) {
  uint32_t regs[32] = {0};
  WORD(ASCON_AXIS_MMIO_STATUS) = ASCON_AXIS_MMIO_STATUS_TX_READY;

  ascon_accel_axis_mmio_transport_ctx_t ctx;
  ascon_accel_axis_mmio_transport_init(&ctx, (uintptr_t)regs, 4u);
  ascon_accel_axis_transport_t transport = ascon_accel_axis_mmio_transport(&ctx);

  const uint8_t payload[19] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
    0x10, 0x11, 0x12,
  };
  if (transport.send(transport.ctx, payload, sizeof(payload), ASCON_ACCEL_STREAM_TEXT) != ASCON_ACCEL_OK) {
    return 1;
  }
  if (ctx.beats_sent != 2u || ctx.last_error != ASCON_ACCEL_OK) {
    return 2;
  }
  if (WORD(ASCON_AXIS_MMIO_TX_DATA0) != 0x00121110u) {
    return 3;
  }
  if (WORD(ASCON_AXIS_MMIO_TX_DATA1) != 0u || WORD(ASCON_AXIS_MMIO_TX_DATA2) != 0u ||
      WORD(ASCON_AXIS_MMIO_TX_DATA3) != 0u) {
    return 4;
  }
  if (WORD(ASCON_AXIS_MMIO_TX_KEEP) != 0x0007u) {
    return 5;
  }
  if (WORD(ASCON_AXIS_MMIO_TX_USER) != ASCON_ACCEL_STREAM_TEXT) {
    return 6;
  }
  if (WORD(ASCON_AXIS_MMIO_TX_CTRL) != (ASCON_AXIS_MMIO_TX_CTRL_VALID | ASCON_AXIS_MMIO_TX_CTRL_LAST)) {
    return 7;
  }
  return 0;
}
''',
    )


def test_axis_mmio_transport_unpacks_final_rx_beat_and_pops_bridge(tmp_path: Path) -> None:
    compile_and_run(
        tmp_path,
        r'''
#include <stdint.h>
#include "ascon_accel_axis_mmio_transport.h"

#define WORD(off) regs[(off) / 4u]

int main(void) {
  uint32_t regs[32] = {0};
  WORD(ASCON_AXIS_MMIO_STATUS) = ASCON_AXIS_MMIO_STATUS_RX_VALID | ASCON_AXIS_MMIO_STATUS_RX_LAST;
  WORD(ASCON_AXIS_MMIO_RX_DATA0) = 0x44332211u;
  WORD(ASCON_AXIS_MMIO_RX_DATA1) = 0x00006655u;
  WORD(ASCON_AXIS_MMIO_RX_KEEP) = 0x003fu;
  WORD(ASCON_AXIS_MMIO_RX_USER) = ASCON_ACCEL_STREAM_TEXT;

  uint8_t out[6] = {0};
  ascon_accel_axis_mmio_transport_ctx_t ctx;
  ascon_accel_axis_mmio_transport_init(&ctx, (uintptr_t)regs, 4u);
  ascon_accel_axis_transport_t transport = ascon_accel_axis_mmio_transport(&ctx);

  if (transport.recv(transport.ctx, out, sizeof(out)) != ASCON_ACCEL_OK) {
    return 1;
  }
  if (ctx.beats_received != 1u || ctx.last_error != ASCON_ACCEL_OK) {
    return 2;
  }
  if (out[0] != 0x11u || out[1] != 0x22u || out[2] != 0x33u ||
      out[3] != 0x44u || out[4] != 0x55u || out[5] != 0x66u) {
    return 3;
  }
  if (WORD(ASCON_AXIS_MMIO_RX_CTRL) != ASCON_AXIS_MMIO_RX_CTRL_POP) {
    return 4;
  }
  return 0;
}
''',
    )


def test_axis_mmio_transport_reports_timeout_and_bad_rx_keep(tmp_path: Path) -> None:
    compile_and_run(
        tmp_path,
        r'''
#include <stdint.h>
#include "ascon_accel_axis_mmio_transport.h"

#define WORD(off) regs[(off) / 4u]

int main(void) {
  uint32_t regs[32] = {0};
  ascon_accel_axis_mmio_transport_ctx_t ctx;
  ascon_accel_axis_mmio_transport_init(&ctx, (uintptr_t)regs, 2u);
  ascon_accel_axis_transport_t transport = ascon_accel_axis_mmio_transport(&ctx);
  const uint8_t byte = 0xa5u;

  if (transport.send(transport.ctx, &byte, 1u, ASCON_ACCEL_STREAM_AD) != ASCON_ACCEL_ERR_TIMEOUT) {
    return 1;
  }
  if (ctx.last_error != ASCON_ACCEL_ERR_TIMEOUT) {
    return 2;
  }

  WORD(ASCON_AXIS_MMIO_STATUS) = ASCON_AXIS_MMIO_STATUS_RX_VALID | ASCON_AXIS_MMIO_STATUS_RX_LAST;
  WORD(ASCON_AXIS_MMIO_RX_KEEP) = 0x0005u;
  uint8_t out[2] = {0};
  if (transport.recv(transport.ctx, out, sizeof(out)) != ASCON_ACCEL_ERR_TRANSPORT) {
    return 3;
  }
  if (ctx.last_error != ASCON_ACCEL_ERR_TRANSPORT) {
    return 4;
  }
  return 0;
}
''',
    )


def test_axis_mmio_transport_is_documented_as_neorv32_bridge_transport() -> None:
    header = (FW / "ascon_accel_axis_mmio_transport.h").read_text(encoding="utf-8")
    source = (FW / "ascon_accel_axis_mmio_transport.c").read_text(encoding="utf-8")
    assert "memory-mapped AXI-stream bridge" in header
    assert "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR" in header
    assert "ASCON_AXIS_MMIO_TX_CTRL_VALID" in header
    assert "ASCON_AXIS_MMIO_RX_CTRL_POP" in header
    assert "keep_is_contiguous_low" in source
    assert "ASCON_AXIS_MMIO_DATA_BYTES" in source
