"""Host-side checks for the descriptor-driven AXI-stream DMA front-end driver.

These mirror tests/test_firmware_axis_transport.py: assert that the public
header and the implementation expose the expected descriptor API and register
map, then compile both the real driver translation unit and a small usage
example with the same strict flags the rest of the firmware uses.  The DMA
*protocol* itself (descriptor -> autonomous payload move -> ciphertext writeback)
is exercised end to end against the RTL by tools/run_stream_axis_dma_system_vector.py
and tests/test_stream_axis_dma_system_sim.py; here we only guard the C surface.
"""

from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware" / "ascon_accel"
HEADER = FW / "ascon_accel_axis_dma_transport.h"
SOURCE = FW / "ascon_accel_axis_dma_transport.c"

_CC = shutil.which("gcc") or shutil.which("cc")
requires_cc = pytest.mark.skipif(_CC is None, reason="no host C compiler (gcc/cc) available")


def test_dma_transport_files_exist() -> None:
    assert HEADER.is_file()
    assert SOURCE.is_file()


def test_public_header_exposes_descriptor_api() -> None:
    header = HEADER.read_text(encoding="utf-8")
    # Context and descriptor types.
    assert "ascon_accel_axis_dma_ctx_t" in header
    assert "ascon_accel_axis_dma_descriptor_t" in header
    # One-shot and staged entry points.
    for symbol in (
        "ascon_accel_axis_dma_init",
        "ascon_accel_axis_dma_clear",
        "ascon_accel_axis_dma_program",
        "ascon_accel_axis_dma_start",
        "ascon_accel_axis_dma_wait_done",
        "ascon_accel_axis_dma_run",
    ):
        assert symbol in header, symbol
    # Descriptor register map and control/status bits.
    for symbol in (
        "ASCON_ACCEL_AXIS_DMA_BASE_ADDR",
        "ASCON_AXIS_DMA_AD_ADDR",
        "ASCON_AXIS_DMA_AD_LEN",
        "ASCON_AXIS_DMA_TEXT_ADDR",
        "ASCON_AXIS_DMA_TEXT_LEN",
        "ASCON_AXIS_DMA_DST_ADDR",
        "ASCON_AXIS_DMA_CTRL",
        "ASCON_AXIS_DMA_STATUS",
        "ASCON_AXIS_DMA_OUT_BYTES",
        "ASCON_AXIS_DMA_CTRL_GO",
        "ASCON_AXIS_DMA_CTRL_IRQ_EN",
        "ASCON_AXIS_DMA_CTRL_CLEAR",
        "ASCON_AXIS_DMA_STATUS_BUSY",
        "ASCON_AXIS_DMA_STATUS_DONE",
        "ASCON_AXIS_DMA_STATUS_ERROR",
    ):
        assert symbol in header, symbol


def test_header_reuses_frozen_csr_status_codes() -> None:
    # The DMA driver layers on top of the existing control-plane API rather than
    # inventing its own error space.
    header = HEADER.read_text(encoding="utf-8")
    assert '#include "ascon_accel.h"' in header
    assert "ascon_accel_status_t" in header


def test_source_maps_status_bits_to_driver_errors() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    # A hardware ERROR flag becomes a transport error; exhausting the poll budget
    # becomes a timeout; bad arguments are rejected before touching the bus.
    assert "ASCON_AXIS_DMA_STATUS_ERROR" in source
    assert "ASCON_ACCEL_ERR_TRANSPORT" in source
    assert "ASCON_ACCEL_ERR_TIMEOUT" in source
    assert "ASCON_ACCEL_ERR_BAD_ARGUMENT" in source
    # Word-addressed memory master => 4-byte alignment is enforced on the host.
    assert "0x3u" in source
    # Completion reports the number of ciphertext bytes written back.
    assert "ASCON_AXIS_DMA_OUT_BYTES" in source


@requires_cc
def test_driver_translation_unit_compiles(tmp_path: Path) -> None:
    obj = tmp_path / "ascon_accel_axis_dma_transport.o"
    subprocess.run(
        [_CC, "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(FW),
         "-c", str(SOURCE), "-o", str(obj)],
        check=True,
        cwd=ROOT,
    )
    assert obj.exists()


@requires_cc
def test_descriptor_usage_example_compiles(tmp_path: Path) -> None:
    example = tmp_path / "axis_dma_example.c"
    example.write_text(
        r"""
#include <stddef.h>
#include <stdint.h>
#include "ascon_accel_axis_dma_transport.h"

/*
 * Autonomous one-shot encryption: the frozen CSR control plane (key, nonce,
 * lengths, mode, CONTROL.START) is assumed already programmed through the
 * ascon_accel CSR API; here we only drive the DMA descriptor that streams the
 * payload through the backend and writes the ciphertext back to dst.
 */
ascon_accel_status_t run_dma_encrypt(
    uintptr_t ad_addr, size_t ad_len,
    uintptr_t text_addr, size_t text_len,
    uintptr_t dst_addr, size_t *out_bytes) {
  ascon_accel_axis_dma_ctx_t ctx;
  ascon_accel_axis_dma_init(&ctx, ASCON_ACCEL_AXIS_DMA_BASE_ADDR, 1000000u, 0);

  ascon_accel_axis_dma_descriptor_t desc = {
    .ad_addr = ad_addr,
    .ad_len = ad_len,
    .text_addr = text_addr,
    .text_len = text_len,
    .dst_addr = dst_addr,
  };
  return ascon_accel_axis_dma_run(&ctx, &desc, out_bytes);
}

/* The staged API must also be usable piecemeal (e.g. with an IRQ handler). */
ascon_accel_status_t run_dma_encrypt_staged(
    const ascon_accel_axis_dma_descriptor_t *desc) {
  ascon_accel_axis_dma_ctx_t ctx;
  ascon_accel_axis_dma_init(&ctx, ASCON_ACCEL_AXIS_DMA_BASE_ADDR, 1000000u, 1);
  ascon_accel_axis_dma_clear(&ctx);
  ascon_accel_status_t st = ascon_accel_axis_dma_program(&ctx, desc);
  if (st != ASCON_ACCEL_OK) {
    return st;
  }
  ascon_accel_axis_dma_start(&ctx);
  return ascon_accel_axis_dma_wait_done(&ctx);
}
""",
        encoding="utf-8",
    )
    obj = tmp_path / "axis_dma_example.o"
    subprocess.run(
        [_CC, "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(FW),
         "-c", str(example), "-o", str(obj)],
        check=True,
        cwd=ROOT,
    )
    assert obj.exists()
