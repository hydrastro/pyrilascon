#include "ascon_accel_axis_ref_emulator.h"

#include <string.h>

#include "../ascon_ref/ascon_ref_aead128.h"

static uint32_t reg_read(const ascon_accel_axis_ref_emulator_ctx_t *ctx, uint32_t offset) {
  return ctx->regs[offset / 4u];
}

static void reg_write(ascon_accel_axis_ref_emulator_ctx_t *ctx, uint32_t offset, uint32_t value) {
  ctx->regs[offset / 4u] = value;
}

static void load_reg_bytes(
    const ascon_accel_axis_ref_emulator_ctx_t *ctx,
    uint32_t base_offset,
    uint8_t *dst,
    size_t len) {
  for (size_t i = 0u; i < len; ++i) {
    const uint32_t word = reg_read(ctx, base_offset + (uint32_t)((i / 4u) * 4u));
    dst[i] = (uint8_t)((word >> (8u * (uint32_t)(i % 4u))) & 0xffu);
  }
}

static void store_reg_bytes(
    ascon_accel_axis_ref_emulator_ctx_t *ctx,
    uint32_t base_offset,
    const uint8_t *src,
    size_t len) {
  for (size_t word_index = 0u; word_index < (len + 3u) / 4u; ++word_index) {
    uint32_t word = 0u;
    for (size_t byte_index = 0u; byte_index < 4u; ++byte_index) {
      const size_t src_index = word_index * 4u + byte_index;
      if (src_index < len) {
        word |= ((uint32_t)src[src_index]) << (8u * (uint32_t)byte_index);
      }
    }
    reg_write(ctx, base_offset + (uint32_t)(word_index * 4u), word);
  }
}

static void set_cycle_count(ascon_accel_axis_ref_emulator_ctx_t *ctx, uint64_t cycles) {
  reg_write(ctx, ASCON_REG_CYCLE_COUNT_LO, (uint32_t)(cycles & UINT64_C(0xffffffff)));
  reg_write(ctx, ASCON_REG_CYCLE_COUNT_HI, (uint32_t)(cycles >> 32u));
}

static void set_error(ascon_accel_axis_ref_emulator_ctx_t *ctx, uint32_t error_code) {
  reg_write(ctx, ASCON_REG_ERROR_CODE, error_code);
  reg_write(ctx, ASCON_REG_STATUS, ASCON_STATUS_DONE | ASCON_STATUS_ERROR);
  ctx->rx_len = 0u;
  ctx->rx_offset = 0u;
  ctx->last_tag_valid = false;
  ctx->completed_operations++;
}

static ascon_accel_status_t append_bytes(
    uint8_t *dst,
    size_t *dst_len,
    const uint8_t *src,
    size_t len) {
  if (*dst_len + len > ASCON_ACCEL_AXIS_REF_EMULATOR_MAX_BYTES) {
    return ASCON_ACCEL_ERR_TRANSPORT;
  }
  if (len != 0u) {
    memcpy(&dst[*dst_len], src, len);
  }
  *dst_len += len;
  return ASCON_ACCEL_OK;
}

static bool expected_lengths_received(const ascon_accel_axis_ref_emulator_ctx_t *ctx) {
  return ctx->ad_len == (size_t)reg_read(ctx, ASCON_REG_AD_LEN) &&
         ctx->text_len == (size_t)reg_read(ctx, ASCON_REG_TEXT_LEN);
}

static void complete_aead128(ascon_accel_axis_ref_emulator_ctx_t *ctx) {
  uint8_t key[ASCON_REF_AEAD128_KEY_BYTES];
  uint8_t nonce[ASCON_REF_AEAD128_NONCE_BYTES];
  uint8_t tag[ASCON_REF_AEAD128_TAG_BYTES];
  const uint32_t control = reg_read(ctx, ASCON_REG_CONTROL);
  const bool decrypt = (control & ASCON_CONTROL_DECRYPT) != 0u;

  if ((control & ASCON_CONTROL_START) == 0u) {
    set_error(ctx, ASCON_ERROR_STREAM_PROTOCOL);
    return;
  }
  if (reg_read(ctx, ASCON_REG_MODE) != ASCON_MODE_AEAD128) {
    set_error(ctx, ASCON_ERROR_UNSUPPORTED_MODE);
    return;
  }
  if (!expected_lengths_received(ctx)) {
    set_error(ctx, ASCON_ERROR_BAD_LENGTH);
    return;
  }

  load_reg_bytes(ctx, ASCON_REG_KEY0, key, sizeof(key));
  load_reg_bytes(ctx, ASCON_REG_NONCE0, nonce, sizeof(nonce));
  ctx->rx_len = 0u;
  ctx->rx_offset = 0u;

  if (decrypt) {
    bool valid = false;
    load_reg_bytes(ctx, ASCON_REG_TAG0, tag, sizeof(tag));
    if (ascon_ref_aead128_decrypt(
            key,
            nonce,
            ctx->ad,
            ctx->ad_len,
            ctx->text,
            ctx->text_len,
            tag,
            ctx->rx,
            &valid) != 0) {
      set_error(ctx, ASCON_ERROR_FAULT_DETECTED);
      return;
    }
    if (!valid) {
      memset(ctx->rx, 0, ctx->text_len);
      set_error(ctx, ASCON_ERROR_TAG_INVALID);
      return;
    }
    ctx->rx_len = ctx->text_len;
    ctx->last_tag_valid = true;
    reg_write(ctx, ASCON_REG_ERROR_CODE, ASCON_ERROR_NONE);
    reg_write(ctx, ASCON_REG_STATUS, ASCON_STATUS_DONE | ASCON_STATUS_TAG_VALID | ASCON_STATUS_OUT_VALID);
  } else {
    if (ascon_ref_aead128_encrypt(
            key,
            nonce,
            ctx->ad,
            ctx->ad_len,
            ctx->text,
            ctx->text_len,
            ctx->rx,
            tag) != 0) {
      set_error(ctx, ASCON_ERROR_FAULT_DETECTED);
      return;
    }
    ctx->rx_len = ctx->text_len;
    ctx->last_tag_valid = true;
    store_reg_bytes(ctx, ASCON_REG_TAG0, tag, sizeof(tag));
    reg_write(ctx, ASCON_REG_ERROR_CODE, ASCON_ERROR_NONE);
    reg_write(ctx, ASCON_REG_STATUS, ASCON_STATUS_DONE | ASCON_STATUS_TAG_VALID | ASCON_STATUS_OUT_VALID);
  }

  ctx->cycle_counter += 48u + (uint64_t)ctx->ad_len + (uint64_t)ctx->text_len;
  set_cycle_count(ctx, ctx->cycle_counter);
  ctx->completed_operations++;
}

void ascon_accel_axis_ref_emulator_init(
    ascon_accel_axis_ref_emulator_ctx_t *ctx,
    volatile uint32_t *regs) {
  if (ctx == 0) {
    return;
  }
  memset(ctx, 0, sizeof(*ctx));
  ctx->regs = regs;
  ctx->last_stream_kind = ASCON_ACCEL_STREAM_TEXT;
  ctx->last_error = ASCON_ACCEL_OK;
  if (regs != 0) {
    reg_write(ctx, ASCON_REG_CAPABILITIES,
        ASCON_CAP_AEAD128 |
        ASCON_CAP_AXI_STREAM_DATA |
        ASCON_CAP_DECRYPT_BUFFERED |
        ASCON_CAP_CONSTTIME_TAG_COMPARE |
        ASCON_CAP_STREAMING_BYTEMASK |
        ASCON_CAP_CYCLE_COUNTER);
    reg_write(ctx, ASCON_REG_ABI_VERSION, ASCON_ACCEL_ABI_VERSION);
    reg_write(ctx, ASCON_REG_STATUS, ASCON_STATUS_DONE);
    reg_write(ctx, ASCON_REG_ERROR_CODE, ASCON_ERROR_NONE);
  }
}

static ascon_accel_status_t emulator_send(
    void *opaque,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t stream_kind) {
  ascon_accel_axis_ref_emulator_ctx_t *ctx = (ascon_accel_axis_ref_emulator_ctx_t *)opaque;
  if (ctx == 0 || ctx->regs == 0 || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }

  ascon_accel_status_t status = ASCON_ACCEL_OK;
  switch (stream_kind) {
    case ASCON_ACCEL_STREAM_AD:
      ctx->ad_len = 0u;
      ctx->text_len = 0u;
      ctx->rx_len = 0u;
      ctx->rx_offset = 0u;
      ctx->last_tag_valid = false;
      status = append_bytes(ctx->ad, &ctx->ad_len, data, len);
      break;
    case ASCON_ACCEL_STREAM_TEXT:
      status = append_bytes(ctx->text, &ctx->text_len, data, len);
      break;
    default:
      status = ASCON_ACCEL_ERR_BAD_ARGUMENT;
      break;
  }

  ctx->send_calls++;
  ctx->last_stream_kind = stream_kind;
  ctx->last_error = status;
  if (status != ASCON_ACCEL_OK) {
    set_error(ctx, ASCON_ERROR_STREAM_PROTOCOL);
    return status;
  }
  if (stream_kind == ASCON_ACCEL_STREAM_TEXT) {
    complete_aead128(ctx);
  }
  return ctx->last_error;
}

static ascon_accel_status_t emulator_recv(void *opaque, uint8_t *data, size_t len) {
  ascon_accel_axis_ref_emulator_ctx_t *ctx = (ascon_accel_axis_ref_emulator_ctx_t *)opaque;
  if (ctx == 0 || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (ctx->rx_offset + len > ctx->rx_len) {
    ctx->recv_calls++;
    ctx->last_error = ASCON_ACCEL_ERR_TRANSPORT;
    return ASCON_ACCEL_ERR_TRANSPORT;
  }
  if (len != 0u) {
    memcpy(data, &ctx->rx[ctx->rx_offset], len);
  }
  ctx->rx_offset += len;
  ctx->recv_calls++;
  ctx->last_error = ASCON_ACCEL_OK;
  return ASCON_ACCEL_OK;
}

ascon_accel_axis_transport_t ascon_accel_axis_ref_emulator_transport(
    ascon_accel_axis_ref_emulator_ctx_t *ctx) {
  ascon_accel_axis_transport_t transport;
  transport.ctx = ctx;
  transport.send = emulator_send;
  transport.recv = emulator_recv;
  return transport;
}
