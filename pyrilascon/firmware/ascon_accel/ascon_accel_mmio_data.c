#include "ascon_accel_internal.h"

void ascon_accel_mmio_stream_bytes(
    const ascon_accel_t *dev,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t stream_kind) {
  size_t offset = 0;
  while (offset < len) {
    uint32_t word = 0;
    uint32_t keep = 0;
    for (uint32_t i = 0; i < 4u; ++i) {
      if (offset < len) {
        word |= ((uint32_t)data[offset]) << (8u * i);
        keep |= 1u << i;
        offset++;
      }
    }
    uint32_t ctrl = ASCON_DATA_VALID | stream_kind | (keep << ASCON_DATA_KEEP_SHIFT);
    if (offset == len) {
      ctrl |= ASCON_DATA_LAST;
    }
    ascon_accel_write_reg(dev, ASCON_REG_DATA_IN, word);
    ascon_accel_write_reg(dev, ASCON_REG_DATA_IN_CTRL, ctrl);
  }
  if (len == 0u) {
    ascon_accel_write_reg(dev, ASCON_REG_DATA_IN, 0u);
    ascon_accel_write_reg(dev, ASCON_REG_DATA_IN_CTRL, ASCON_DATA_VALID | ASCON_DATA_LAST | stream_kind);
  }
}

void ascon_accel_mmio_read_bytes(const ascon_accel_t *dev, uint8_t *data, size_t len) {
  size_t offset = 0;
  while (offset < len) {
    uint32_t word = ascon_accel_read_reg(dev, ASCON_REG_DATA_OUT);
    for (uint32_t i = 0; i < 4u && offset < len; ++i) {
      data[offset++] = (uint8_t)((word >> (8u * i)) & 0xffu);
    }
    (void)ascon_accel_read_reg(dev, ASCON_REG_DATA_OUT_CTRL);
  }
}
