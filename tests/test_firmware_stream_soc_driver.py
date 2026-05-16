from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware" / "ascon_accel"


def test_firmware_starts_stream_backend_before_axis_payload_and_maps_tag_invalid(tmp_path: Path) -> None:
    program = tmp_path / "stream_soc_driver_sequence.c"
    program.write_text(
        r'''
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "ascon_accel.h"

typedef struct {
  uint32_t *regs;
  uint8_t rx[64];
  size_t rx_len;
  size_t rx_offset;
  unsigned send_calls;
  unsigned recv_calls;
  unsigned saw_start_before_first_send;
  unsigned saw_decrypt_before_first_send;
  int invalid_tag;
} test_ctx_t;

static ascon_accel_status_t send_cb(
    void *opaque,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t kind) {
  test_ctx_t *ctx = (test_ctx_t *)opaque;
  (void)data;
  (void)len;
  if (ctx == 0) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (ctx->send_calls == 0u) {
    ctx->saw_start_before_first_send = (ctx->regs[ASCON_REG_CONTROL / 4u] & ASCON_CONTROL_START) != 0u;
    ctx->saw_decrypt_before_first_send = (ctx->regs[ASCON_REG_CONTROL / 4u] & ASCON_CONTROL_DECRYPT) != 0u;
  }
  ctx->send_calls++;
  if (kind == ASCON_ACCEL_STREAM_TEXT) {
    if (ctx->invalid_tag) {
      ctx->regs[ASCON_REG_ERROR_CODE / 4u] = ASCON_ERROR_TAG_INVALID;
      ctx->regs[ASCON_REG_STATUS / 4u] = ASCON_STATUS_DONE | ASCON_STATUS_ERROR;
    } else {
      ctx->regs[ASCON_REG_TAG0 / 4u] = 0x03020100u;
      ctx->regs[ASCON_REG_TAG1 / 4u] = 0x07060504u;
      ctx->regs[ASCON_REG_TAG2 / 4u] = 0x0b0a0908u;
      ctx->regs[ASCON_REG_TAG3 / 4u] = 0x0f0e0d0cu;
      ctx->regs[ASCON_REG_ERROR_CODE / 4u] = ASCON_ERROR_NONE;
      ctx->regs[ASCON_REG_STATUS / 4u] = ASCON_STATUS_DONE | ASCON_STATUS_TAG_VALID;
    }
  }
  return ASCON_ACCEL_OK;
}

static ascon_accel_status_t recv_cb(void *opaque, uint8_t *data, size_t len) {
  test_ctx_t *ctx = (test_ctx_t *)opaque;
  if (ctx == 0 || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (ctx->rx_offset + len > ctx->rx_len) {
    return ASCON_ACCEL_ERR_TRANSPORT;
  }
  memcpy(data, &ctx->rx[ctx->rx_offset], len);
  ctx->rx_offset += len;
  ctx->recv_calls++;
  return ASCON_ACCEL_OK;
}

static int run_encrypt_case(void) {
  uint32_t regs[64] = {0};
  test_ctx_t ctx;
  memset(&ctx, 0, sizeof(ctx));
  ctx.regs = regs;
  ctx.rx[0] = 0xa0u;
  ctx.rx[1] = 0xa1u;
  ctx.rx[2] = 0xa2u;
  ctx.rx_len = 3u;
  regs[ASCON_REG_CAPABILITIES / 4u] = ASCON_CAP_AEAD128 | ASCON_CAP_AXI_STREAM_DATA;
  regs[ASCON_REG_ABI_VERSION / 4u] = ASCON_ACCEL_ABI_VERSION;

  ascon_accel_t dev;
  ascon_accel_init(&dev, (uintptr_t)regs, 1000u);
  ascon_accel_axis_transport_t transport = {&ctx, send_cb, recv_cb};
  ascon_accel_set_axis_transport(&dev, &transport);
  ascon_accel_set_data_plane(&dev, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL);

  const uint8_t key[16] = {0};
  const uint8_t nonce[16] = {0};
  const uint8_t ad[2] = {0x11u, 0x22u};
  const uint8_t plaintext[3] = {0x33u, 0x44u, 0x55u};
  uint8_t ciphertext[3] = {0};
  ascon_accel_aead_request_t req = {key, nonce, ad, sizeof(ad), plaintext, sizeof(plaintext), ciphertext, {0}};

  if (ascon_accel_encrypt(&dev, ASCON_ACCEL_MODE_AEAD128, &req) != ASCON_ACCEL_OK) {
    return 1;
  }
  if (!ctx.saw_start_before_first_send || ctx.saw_decrypt_before_first_send) {
    return 2;
  }
  if (ctx.send_calls != 2u || ctx.recv_calls != 1u) {
    return 3;
  }
  if (ciphertext[0] != 0xa0u || ciphertext[1] != 0xa1u || ciphertext[2] != 0xa2u) {
    return 4;
  }
  if (req.tag[0] != 0x00u || req.tag[15] != 0x0fu) {
    return 5;
  }
  return 0;
}

static int run_decrypt_invalid_tag_case(void) {
  uint32_t regs[64] = {0};
  test_ctx_t ctx;
  memset(&ctx, 0, sizeof(ctx));
  ctx.regs = regs;
  ctx.invalid_tag = 1;
  regs[ASCON_REG_CAPABILITIES / 4u] = ASCON_CAP_AEAD128 | ASCON_CAP_AXI_STREAM_DATA | ASCON_CAP_DECRYPT_BUFFERED;
  regs[ASCON_REG_ABI_VERSION / 4u] = ASCON_ACCEL_ABI_VERSION;

  ascon_accel_t dev;
  ascon_accel_init(&dev, (uintptr_t)regs, 1000u);
  ascon_accel_axis_transport_t transport = {&ctx, send_cb, recv_cb};
  ascon_accel_set_axis_transport(&dev, &transport);
  ascon_accel_set_data_plane(&dev, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL);

  const uint8_t key[16] = {0};
  const uint8_t nonce[16] = {0};
  const uint8_t ciphertext[3] = {0x33u, 0x44u, 0x55u};
  uint8_t plaintext[3] = {0};
  ascon_accel_aead_request_t req = {key, nonce, 0, 0u, ciphertext, sizeof(ciphertext), plaintext, {0}};

  if (ascon_accel_decrypt(&dev, ASCON_ACCEL_MODE_AEAD128, &req) != ASCON_ACCEL_ERR_TAG_INVALID) {
    return 10;
  }
  if (!ctx.saw_start_before_first_send || !ctx.saw_decrypt_before_first_send) {
    return 11;
  }
  if (ctx.send_calls != 2u || ctx.recv_calls != 0u) {
    return 12;
  }
  return 0;
}

int main(void) {
  int status = run_encrypt_case();
  if (status != 0) {
    return status;
  }
  return run_decrypt_invalid_tag_case();
}
''',
        encoding="utf-8",
    )
    exe = tmp_path / "stream_soc_driver_sequence"
    sources = [
        FW / "ascon_accel.c",
        FW / "ascon_accel_control.c",
        FW / "ascon_accel_caps.c",
        FW / "ascon_accel_mmio_data.c",
        FW / "ascon_accel_axis_data.c",
    ]
    subprocess.run(
        ["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(FW), str(program), *map(str, sources), "-o", str(exe)],
        check=True,
        cwd=ROOT,
    )
    subprocess.run([str(exe)], check=True, cwd=ROOT)


def test_firmware_source_documents_split_mmio_and_stream_start_order() -> None:
    source = (FW / "ascon_accel.c").read_text(encoding="utf-8")
    assert "request_uses_axis_data_plane" in source
    assert "request_uses_mmio_data_plane" in source
    assert "complete_operation_status" in source
    assert "ASCON_CONTROL_START | ASCON_CONTROL_DECRYPT" in source
    assert "ascon_accel_status_from_error_code" in source
