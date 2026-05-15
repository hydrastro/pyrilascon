#include "ascon_accel_internal.h"

ascon_accel_status_t ascon_accel_axis_stream_bytes(
    const ascon_accel_t *dev,
    const uint8_t *data,
    size_t len,
    uint32_t stream_kind) {
  (void)dev;
  (void)data;
  (void)len;
  (void)stream_kind;
  return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
}

ascon_accel_status_t ascon_accel_axis_read_bytes(const ascon_accel_t *dev, uint8_t *data, size_t len) {
  (void)dev;
  (void)data;
  (void)len;
  return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
}
