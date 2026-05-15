#ifndef ASCON_ACCEL_AXIS_MOCK_TRANSPORT_H
#define ASCON_ACCEL_AXIS_MOCK_TRANSPORT_H

#include <stddef.h>
#include <stdint.h>

#include "ascon_accel.h"

#ifdef __cplusplus
extern "C" {
#endif

#ifndef ASCON_ACCEL_AXIS_MOCK_MAX_BYTES
#define ASCON_ACCEL_AXIS_MOCK_MAX_BYTES 4096u
#endif

typedef struct {
  uint8_t ad[ASCON_ACCEL_AXIS_MOCK_MAX_BYTES];
  uint8_t text[ASCON_ACCEL_AXIS_MOCK_MAX_BYTES];
  uint8_t custom[ASCON_ACCEL_AXIS_MOCK_MAX_BYTES];
  uint8_t rx[ASCON_ACCEL_AXIS_MOCK_MAX_BYTES];

  size_t ad_len;
  size_t text_len;
  size_t custom_len;
  size_t rx_len;
  size_t rx_offset;

  uint32_t send_calls;
  uint32_t recv_calls;
  ascon_accel_stream_kind_t last_stream_kind;
  ascon_accel_status_t last_error;
} ascon_accel_axis_mock_transport_ctx_t;

void ascon_accel_axis_mock_init(ascon_accel_axis_mock_transport_ctx_t *ctx);
ascon_accel_axis_transport_t ascon_accel_axis_mock_transport(
    ascon_accel_axis_mock_transport_ctx_t *ctx);
ascon_accel_status_t ascon_accel_axis_mock_load_rx(
    ascon_accel_axis_mock_transport_ctx_t *ctx,
    const uint8_t *data,
    size_t len);

#ifdef __cplusplus
}
#endif

#endif
