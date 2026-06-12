#include "ascon_accel_axis_dma_transport.h"

static volatile uint32_t *dma_reg(const ascon_accel_axis_dma_ctx_t *ctx, uint32_t offset) {
  return (volatile uint32_t *)(ctx->base_addr + (uintptr_t)offset);
}

static uint32_t dma_read(const ascon_accel_axis_dma_ctx_t *ctx, uint32_t offset) {
  return *dma_reg(ctx, offset);
}

static void dma_write(const ascon_accel_axis_dma_ctx_t *ctx, uint32_t offset, uint32_t value) {
  *dma_reg(ctx, offset) = value;
}

void ascon_accel_axis_dma_init(
    ascon_accel_axis_dma_ctx_t *ctx,
    uintptr_t base_addr,
    uint32_t timeout_cycles,
    int irq_enabled) {
  if (ctx == 0) {
    return;
  }
  ctx->base_addr = base_addr;
  ctx->timeout_cycles = timeout_cycles;
  ctx->irq_enabled = irq_enabled ? 1 : 0;
  ctx->last_status = 0u;
  ctx->last_out_bytes = 0u;
  ctx->last_error = ASCON_ACCEL_OK;
}

void ascon_accel_axis_dma_clear(ascon_accel_axis_dma_ctx_t *ctx) {
  if (ctx == 0 || ctx->base_addr == 0u) {
    return;
  }
  dma_write(ctx, ASCON_AXIS_DMA_CTRL, ASCON_AXIS_DMA_CTRL_CLEAR);
}

ascon_accel_status_t ascon_accel_axis_dma_program(
    ascon_accel_axis_dma_ctx_t *ctx,
    const ascon_accel_axis_dma_descriptor_t *desc) {
  if (ctx == 0 || ctx->base_addr == 0u || desc == 0) {
    if (ctx != 0) {
      ctx->last_error = ASCON_ACCEL_ERR_BAD_ARGUMENT;
    }
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  /* The descriptor registers carry word-addressable buffers; reject anything
   * that is not 4-byte aligned, since the DMA addresses memory by 32-bit word. */
  if (((uint32_t)desc->ad_addr & 0x3u) != 0u ||
      ((uint32_t)desc->text_addr & 0x3u) != 0u ||
      ((uint32_t)desc->dst_addr & 0x3u) != 0u) {
    ctx->last_error = ASCON_ACCEL_ERR_BAD_ARGUMENT;
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }

  dma_write(ctx, ASCON_AXIS_DMA_AD_ADDR, (uint32_t)desc->ad_addr);
  dma_write(ctx, ASCON_AXIS_DMA_AD_LEN, (uint32_t)desc->ad_len);
  dma_write(ctx, ASCON_AXIS_DMA_TEXT_ADDR, (uint32_t)desc->text_addr);
  dma_write(ctx, ASCON_AXIS_DMA_TEXT_LEN, (uint32_t)desc->text_len);
  dma_write(ctx, ASCON_AXIS_DMA_DST_ADDR, (uint32_t)desc->dst_addr);
  ctx->last_error = ASCON_ACCEL_OK;
  return ASCON_ACCEL_OK;
}

void ascon_accel_axis_dma_start(ascon_accel_axis_dma_ctx_t *ctx) {
  if (ctx == 0 || ctx->base_addr == 0u) {
    return;
  }
  uint32_t ctrl = ASCON_AXIS_DMA_CTRL_GO;
  if (ctx->irq_enabled) {
    ctrl |= ASCON_AXIS_DMA_CTRL_IRQ_EN;
  }
  dma_write(ctx, ASCON_AXIS_DMA_CTRL, ctrl);
}

ascon_accel_status_t ascon_accel_axis_dma_wait_done(ascon_accel_axis_dma_ctx_t *ctx) {
  if (ctx == 0 || ctx->base_addr == 0u) {
    if (ctx != 0) {
      ctx->last_error = ASCON_ACCEL_ERR_BAD_ARGUMENT;
    }
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  for (uint32_t i = 0u; i < ctx->timeout_cycles; ++i) {
    const uint32_t status = dma_read(ctx, ASCON_AXIS_DMA_STATUS);
    if ((status & ASCON_AXIS_DMA_STATUS_ERROR) != 0u) {
      ctx->last_status = status;
      ctx->last_error = ASCON_ACCEL_ERR_TRANSPORT;
      return ASCON_ACCEL_ERR_TRANSPORT;
    }
    if ((status & ASCON_AXIS_DMA_STATUS_DONE) != 0u) {
      ctx->last_status = status;
      ctx->last_out_bytes = dma_read(ctx, ASCON_AXIS_DMA_OUT_BYTES);
      ctx->last_error = ASCON_ACCEL_OK;
      return ASCON_ACCEL_OK;
    }
  }
  ctx->last_status = dma_read(ctx, ASCON_AXIS_DMA_STATUS);
  ctx->last_error = ASCON_ACCEL_ERR_TIMEOUT;
  return ASCON_ACCEL_ERR_TIMEOUT;
}

ascon_accel_status_t ascon_accel_axis_dma_run(
    ascon_accel_axis_dma_ctx_t *ctx,
    const ascon_accel_axis_dma_descriptor_t *desc,
    size_t *out_bytes) {
  ascon_accel_status_t status;
  /* CLEAR first: it drops any latched DONE/ERROR from a prior transfer while
   * leaving the descriptor registers untouched, so program the descriptor
   * afterwards.  This mirrors the cosim sequence (CLEAR, descriptor, GO). */
  ascon_accel_axis_dma_clear(ctx);
  status = ascon_accel_axis_dma_program(ctx, desc);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  ascon_accel_axis_dma_start(ctx);
  status = ascon_accel_axis_dma_wait_done(ctx);
  if (status == ASCON_ACCEL_OK && out_bytes != 0) {
    *out_bytes = (size_t)ctx->last_out_bytes;
  }
  return status;
}
