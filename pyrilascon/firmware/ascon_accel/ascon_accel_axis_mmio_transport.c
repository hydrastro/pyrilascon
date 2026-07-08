#include "ascon_accel_axis_mmio_transport.h"

static volatile uint32_t *axis_reg(const ascon_accel_axis_mmio_transport_ctx_t *ctx, uint32_t offset) {
  return (volatile uint32_t *)(ctx->base_addr + (uintptr_t)offset);
}

static uint32_t axis_read(const ascon_accel_axis_mmio_transport_ctx_t *ctx, uint32_t offset) {
  return *axis_reg(ctx, offset);
}

static void axis_write(const ascon_accel_axis_mmio_transport_ctx_t *ctx, uint32_t offset, uint32_t value) {
  *axis_reg(ctx, offset) = value;
}

static uint32_t load_le32(const uint8_t *src, size_t available) {
  uint32_t word = 0u;
  for (size_t i = 0u; i < 4u && i < available; ++i) {
    word |= ((uint32_t)src[i]) << (8u * i);
  }
  return word;
}

static void store_le32(uint8_t *dst, size_t available, uint32_t word) {
  for (size_t i = 0u; i < 4u && i < available; ++i) {
    dst[i] = (uint8_t)((word >> (8u * i)) & 0xffu);
  }
}

static uint32_t keep_for_len(size_t len) {
  if (len >= ASCON_AXIS_MMIO_DATA_BYTES) {
    return ASCON_AXIS_MMIO_KEEP_FULL;
  }
  return (len == 0u) ? 0u : ((1u << len) - 1u);
}

static size_t popcount16(uint32_t value) {
  size_t count = 0u;
  value &= ASCON_AXIS_MMIO_KEEP_FULL;
  while (value != 0u) {
    count += (size_t)(value & 1u);
    value >>= 1u;
  }
  return count;
}

static int keep_is_contiguous_low(uint32_t keep) {
  keep &= ASCON_AXIS_MMIO_KEEP_FULL;
  if (keep == 0u) {
    return 0;
  }
  return (keep & (keep + 1u)) == 0u;
}

static ascon_accel_status_t wait_for_bits(
    ascon_accel_axis_mmio_transport_ctx_t *ctx,
    uint32_t mask) {
  if (ctx == 0 || ctx->base_addr == 0u) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  for (uint32_t i = 0u; i < ctx->timeout_cycles; ++i) {
    const uint32_t status = axis_read(ctx, ASCON_AXIS_MMIO_STATUS);
    if ((status & ASCON_AXIS_MMIO_STATUS_ERROR) != 0u) {
      ctx->last_error = ASCON_ACCEL_ERR_TRANSPORT;
      return ASCON_ACCEL_ERR_TRANSPORT;
    }
    if ((status & mask) == mask) {
      ctx->last_error = ASCON_ACCEL_OK;
      return ASCON_ACCEL_OK;
    }
  }
  ctx->last_error = ASCON_ACCEL_ERR_TIMEOUT;
  return ASCON_ACCEL_ERR_TIMEOUT;
}

void ascon_accel_axis_mmio_transport_init(
    ascon_accel_axis_mmio_transport_ctx_t *ctx,
    uintptr_t base_addr,
    uint32_t timeout_cycles) {
  if (ctx == 0) {
    return;
  }
  ctx->base_addr = base_addr;
  ctx->timeout_cycles = timeout_cycles;
  ctx->beats_sent = 0u;
  ctx->beats_received = 0u;
  ctx->last_error = ASCON_ACCEL_OK;
}

static ascon_accel_status_t axis_mmio_send(
    void *opaque,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t stream_kind) {
  ascon_accel_axis_mmio_transport_ctx_t *ctx = (ascon_accel_axis_mmio_transport_ctx_t *)opaque;
  if (ctx == 0 || ctx->base_addr == 0u || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (stream_kind != ASCON_ACCEL_STREAM_AD &&
      stream_kind != ASCON_ACCEL_STREAM_TEXT &&
      stream_kind != ASCON_ACCEL_STREAM_CUSTOM) {
    ctx->last_error = ASCON_ACCEL_ERR_BAD_ARGUMENT;
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (len == 0u) {
    ctx->last_error = ASCON_ACCEL_OK;
    return ASCON_ACCEL_OK;
  }

  size_t offset = 0u;
  while (offset < len) {
    const size_t remaining = len - offset;
    const size_t beat_len = remaining < ASCON_AXIS_MMIO_DATA_BYTES ? remaining : ASCON_AXIS_MMIO_DATA_BYTES;
    const uint32_t keep = keep_for_len(beat_len);
    const uint32_t last = (offset + beat_len == len) ? ASCON_AXIS_MMIO_TX_CTRL_LAST : 0u;

    ascon_accel_status_t status = wait_for_bits(ctx, ASCON_AXIS_MMIO_STATUS_TX_READY);
    if (status != ASCON_ACCEL_OK) {
      return status;
    }

    axis_write(ctx, ASCON_AXIS_MMIO_TX_DATA0, load_le32(&data[offset], beat_len));
    axis_write(ctx, ASCON_AXIS_MMIO_TX_DATA1,
               beat_len > 4u ? load_le32(&data[offset + 4u], beat_len - 4u) : 0u);
    axis_write(ctx, ASCON_AXIS_MMIO_TX_DATA2,
               beat_len > 8u ? load_le32(&data[offset + 8u], beat_len - 8u) : 0u);
    axis_write(ctx, ASCON_AXIS_MMIO_TX_DATA3,
               beat_len > 12u ? load_le32(&data[offset + 12u], beat_len - 12u) : 0u);
    axis_write(ctx, ASCON_AXIS_MMIO_TX_KEEP, keep);
    axis_write(ctx, ASCON_AXIS_MMIO_TX_USER, (uint32_t)stream_kind);
    axis_write(ctx, ASCON_AXIS_MMIO_TX_CTRL, ASCON_AXIS_MMIO_TX_CTRL_VALID | last);

    ctx->beats_sent++;
    offset += beat_len;
  }
  ctx->last_error = ASCON_ACCEL_OK;
  return ASCON_ACCEL_OK;
}

static ascon_accel_status_t axis_mmio_recv(void *opaque, uint8_t *data, size_t len) {
  ascon_accel_axis_mmio_transport_ctx_t *ctx = (ascon_accel_axis_mmio_transport_ctx_t *)opaque;
  if (ctx == 0 || ctx->base_addr == 0u || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (len == 0u) {
    ctx->last_error = ASCON_ACCEL_OK;
    return ASCON_ACCEL_OK;
  }

  size_t offset = 0u;
  while (offset < len) {
    ascon_accel_status_t status = wait_for_bits(ctx, ASCON_AXIS_MMIO_STATUS_RX_VALID);
    if (status != ASCON_ACCEL_OK) {
      return status;
    }

    const uint32_t keep = axis_read(ctx, ASCON_AXIS_MMIO_RX_KEEP) & ASCON_AXIS_MMIO_KEEP_FULL;
    if (!keep_is_contiguous_low(keep)) {
      ctx->last_error = ASCON_ACCEL_ERR_TRANSPORT;
      return ASCON_ACCEL_ERR_TRANSPORT;
    }
    const size_t beat_len = popcount16(keep);
    if (offset + beat_len > len) {
      ctx->last_error = ASCON_ACCEL_ERR_TRANSPORT;
      return ASCON_ACCEL_ERR_TRANSPORT;
    }

    const uint32_t w0 = axis_read(ctx, ASCON_AXIS_MMIO_RX_DATA0);
    const uint32_t w1 = axis_read(ctx, ASCON_AXIS_MMIO_RX_DATA1);
    const uint32_t w2 = axis_read(ctx, ASCON_AXIS_MMIO_RX_DATA2);
    const uint32_t w3 = axis_read(ctx, ASCON_AXIS_MMIO_RX_DATA3);
    store_le32(&data[offset], beat_len, w0);
    if (beat_len > 4u) {
      store_le32(&data[offset + 4u], beat_len - 4u, w1);
    }
    if (beat_len > 8u) {
      store_le32(&data[offset + 8u], beat_len - 8u, w2);
    }
    if (beat_len > 12u) {
      store_le32(&data[offset + 12u], beat_len - 12u, w3);
    }

    offset += beat_len;
    ctx->beats_received++;
    axis_write(ctx, ASCON_AXIS_MMIO_RX_CTRL, ASCON_AXIS_MMIO_RX_CTRL_POP);

    const uint32_t status_word = axis_read(ctx, ASCON_AXIS_MMIO_STATUS);
    if (offset == len && (status_word & ASCON_AXIS_MMIO_STATUS_RX_LAST) == 0u) {
      ctx->last_error = ASCON_ACCEL_ERR_TRANSPORT;
      return ASCON_ACCEL_ERR_TRANSPORT;
    }
    if (offset < len && (status_word & ASCON_AXIS_MMIO_STATUS_RX_LAST) != 0u) {
      ctx->last_error = ASCON_ACCEL_ERR_TRANSPORT;
      return ASCON_ACCEL_ERR_TRANSPORT;
    }
  }

  ctx->last_error = ASCON_ACCEL_OK;
  return ASCON_ACCEL_OK;
}

ascon_accel_axis_transport_t ascon_accel_axis_mmio_transport(
    ascon_accel_axis_mmio_transport_ctx_t *ctx) {
  ascon_accel_axis_transport_t transport;
  transport.ctx = ctx;
  transport.send = axis_mmio_send;
  transport.recv = axis_mmio_recv;
  return transport;
}
