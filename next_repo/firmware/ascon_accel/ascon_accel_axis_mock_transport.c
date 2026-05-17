#include "ascon_accel_axis_mock_transport.h"

static void ascon_mock_copy(uint8_t *dst, const uint8_t *src, size_t len) {
  for (size_t i = 0; i < len; ++i) {
    dst[i] = src[i];
  }
}

void ascon_accel_axis_mock_init(ascon_accel_axis_mock_transport_ctx_t *ctx) {
  if (ctx == 0) {
    return;
  }
  ctx->ad_len = 0u;
  ctx->text_len = 0u;
  ctx->custom_len = 0u;
  ctx->rx_len = 0u;
  ctx->rx_offset = 0u;
  ctx->send_calls = 0u;
  ctx->recv_calls = 0u;
  ctx->last_stream_kind = ASCON_ACCEL_STREAM_TEXT;
  ctx->last_error = ASCON_ACCEL_OK;
}

ascon_accel_status_t ascon_accel_axis_mock_load_rx(
    ascon_accel_axis_mock_transport_ctx_t *ctx,
    const uint8_t *data,
    size_t len) {
  if (ctx == 0 || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (len > ASCON_ACCEL_AXIS_MOCK_MAX_BYTES) {
    ctx->last_error = ASCON_ACCEL_ERR_TRANSPORT;
    return ASCON_ACCEL_ERR_TRANSPORT;
  }
  ascon_mock_copy(ctx->rx, data, len);
  ctx->rx_len = len;
  ctx->rx_offset = 0u;
  ctx->last_error = ASCON_ACCEL_OK;
  return ASCON_ACCEL_OK;
}

static ascon_accel_status_t ascon_axis_mock_append(
    uint8_t *dst,
    size_t *dst_len,
    const uint8_t *data,
    size_t len) {
  if (*dst_len + len > ASCON_ACCEL_AXIS_MOCK_MAX_BYTES) {
    return ASCON_ACCEL_ERR_TRANSPORT;
  }
  ascon_mock_copy(&dst[*dst_len], data, len);
  *dst_len += len;
  return ASCON_ACCEL_OK;
}

static ascon_accel_status_t ascon_axis_mock_send(
    void *opaque,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t stream_kind) {
  ascon_accel_axis_mock_transport_ctx_t *ctx = (ascon_accel_axis_mock_transport_ctx_t *)opaque;
  if (ctx == 0 || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }

  ascon_accel_status_t status;
  switch (stream_kind) {
    case ASCON_ACCEL_STREAM_AD:
      status = ascon_axis_mock_append(ctx->ad, &ctx->ad_len, data, len);
      break;
    case ASCON_ACCEL_STREAM_TEXT:
      status = ascon_axis_mock_append(ctx->text, &ctx->text_len, data, len);
      break;
    case ASCON_ACCEL_STREAM_CUSTOM:
      status = ascon_axis_mock_append(ctx->custom, &ctx->custom_len, data, len);
      break;
    default:
      status = ASCON_ACCEL_ERR_BAD_ARGUMENT;
      break;
  }

  ctx->send_calls++;
  ctx->last_stream_kind = stream_kind;
  ctx->last_error = status;
  return status;
}

static ascon_accel_status_t ascon_axis_mock_recv(void *opaque, uint8_t *data, size_t len) {
  ascon_accel_axis_mock_transport_ctx_t *ctx = (ascon_accel_axis_mock_transport_ctx_t *)opaque;
  if (ctx == 0 || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (ctx->rx_offset + len > ctx->rx_len) {
    ctx->recv_calls++;
    ctx->last_error = ASCON_ACCEL_ERR_TRANSPORT;
    return ASCON_ACCEL_ERR_TRANSPORT;
  }

  ascon_mock_copy(data, &ctx->rx[ctx->rx_offset], len);
  ctx->rx_offset += len;
  ctx->recv_calls++;
  ctx->last_error = ASCON_ACCEL_OK;
  return ASCON_ACCEL_OK;
}

ascon_accel_axis_transport_t ascon_accel_axis_mock_transport(
    ascon_accel_axis_mock_transport_ctx_t *ctx) {
  ascon_accel_axis_transport_t transport;
  transport.ctx = ctx;
  transport.send = ascon_axis_mock_send;
  transport.recv = ascon_axis_mock_recv;
  return transport;
}
