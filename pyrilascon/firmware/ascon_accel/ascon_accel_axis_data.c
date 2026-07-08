#include "ascon_accel_internal.h"

static bool ascon_accel_has_axis_data_plane(const ascon_accel_t *dev) {
  return (ascon_accel_capabilities(dev) & ASCON_CAP_AXI_STREAM_DATA) != 0u;
}

bool ascon_accel_axis_transport_configured(const ascon_accel_t *dev) {
  return dev != 0 && dev->axis_transport.send != 0 && dev->axis_transport.recv != 0;
}

void ascon_accel_set_axis_transport(
    ascon_accel_t *dev,
    const ascon_accel_axis_transport_t *transport) {
  if (dev == 0) {
    return;
  }
  if (transport == 0) {
    dev->axis_transport.ctx = 0;
    dev->axis_transport.send = 0;
    dev->axis_transport.recv = 0;
    return;
  }
  dev->axis_transport = *transport;
}

ascon_accel_status_t ascon_accel_axis_stream_bytes(
    const ascon_accel_t *dev,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t stream_kind) {
  if (dev == 0 || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (!ascon_accel_has_axis_data_plane(dev)) {
    return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
  }
  if (!ascon_accel_axis_transport_configured(dev)) {
    return ASCON_ACCEL_ERR_TRANSPORT;
  }
  return dev->axis_transport.send(dev->axis_transport.ctx, data, len, stream_kind);
}

ascon_accel_status_t ascon_accel_axis_read_bytes(const ascon_accel_t *dev, uint8_t *data, size_t len) {
  if (dev == 0 || (len != 0u && data == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (!ascon_accel_has_axis_data_plane(dev)) {
    return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
  }
  if (!ascon_accel_axis_transport_configured(dev)) {
    return ASCON_ACCEL_ERR_TRANSPORT;
  }
  return dev->axis_transport.recv(dev->axis_transport.ctx, data, len);
}
