#include "ascon_accel_internal.h"

volatile uint32_t *ascon_accel_reg(const ascon_accel_t *dev, uint32_t offset) {
  return (volatile uint32_t *)(dev->base_addr + (uintptr_t)offset);
}

void ascon_accel_write_reg(const ascon_accel_t *dev, uint32_t offset, uint32_t value) {
  *ascon_accel_reg(dev, offset) = value;
}

uint32_t ascon_accel_read_reg(const ascon_accel_t *dev, uint32_t offset) {
  return *ascon_accel_reg(dev, offset);
}

uint32_t ascon_accel_load32_le(const uint8_t *p) {
  return ((uint32_t)p[0]) |
         ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}

void ascon_accel_store32_le(uint8_t *p, uint32_t x) {
  p[0] = (uint8_t)(x & 0xffu);
  p[1] = (uint8_t)((x >> 8) & 0xffu);
  p[2] = (uint8_t)((x >> 16) & 0xffu);
  p[3] = (uint8_t)((x >> 24) & 0xffu);
}

ascon_accel_status_t ascon_accel_wait_done(const ascon_accel_t *dev) {
  uint32_t timeout = dev->timeout_cycles;
  while (timeout-- != 0u) {
    uint32_t status = ascon_accel_read_reg(dev, ASCON_REG_STATUS);
    if ((status & ASCON_STATUS_ERROR) != 0u) {
      return ASCON_ACCEL_ERR_HARDWARE_ERROR;
    }
    if ((status & ASCON_STATUS_DONE) != 0u) {
      return ASCON_ACCEL_OK;
    }
  }
  return ASCON_ACCEL_ERR_TIMEOUT;
}

void ascon_accel_init(ascon_accel_t *dev, uintptr_t base_addr, uint32_t timeout_cycles) {
  if (dev == 0) {
    return;
  }
  dev->base_addr = base_addr;
  dev->timeout_cycles = timeout_cycles;
  dev->data_plane = ASCON_ACCEL_DATA_PLANE_MMIO_WORD;
}

void ascon_accel_set_data_plane(ascon_accel_t *dev, ascon_accel_data_plane_t data_plane) {
  if (dev == 0) {
    return;
  }
  dev->data_plane = data_plane;
}

void ascon_accel_reset(const ascon_accel_t *dev) {
  ascon_accel_write_reg(dev, ASCON_REG_CONTROL, ASCON_CONTROL_CLEAR);
}

uint32_t ascon_accel_error_code(const ascon_accel_t *dev) {
  return ascon_accel_read_reg(dev, ASCON_REG_ERROR_CODE);
}

uint64_t ascon_accel_cycle_count(const ascon_accel_t *dev) {
  uint32_t hi0;
  uint32_t lo;
  uint32_t hi1;
  do {
    hi0 = ascon_accel_read_reg(dev, ASCON_REG_CYCLE_COUNT_HI);
    lo = ascon_accel_read_reg(dev, ASCON_REG_CYCLE_COUNT_LO);
    hi1 = ascon_accel_read_reg(dev, ASCON_REG_CYCLE_COUNT_HI);
  } while (hi0 != hi1);
  return ((uint64_t)hi1 << 32) | (uint64_t)lo;
}

bool ascon_accel_busy(const ascon_accel_t *dev) {
  return (ascon_accel_read_reg(dev, ASCON_REG_STATUS) & ASCON_STATUS_BUSY) != 0u;
}

bool ascon_accel_done(const ascon_accel_t *dev) {
  return (ascon_accel_read_reg(dev, ASCON_REG_STATUS) & ASCON_STATUS_DONE) != 0u;
}

bool ascon_accel_tag_valid(const ascon_accel_t *dev) {
  return (ascon_accel_read_reg(dev, ASCON_REG_STATUS) & ASCON_STATUS_TAG_VALID) != 0u;
}

void ascon_accel_write_key_128(const ascon_accel_t *dev, const uint8_t *key) {
  ascon_accel_write_reg(dev, ASCON_REG_KEY0, ascon_accel_load32_le(&key[0]));
  ascon_accel_write_reg(dev, ASCON_REG_KEY1, ascon_accel_load32_le(&key[4]));
  ascon_accel_write_reg(dev, ASCON_REG_KEY2, ascon_accel_load32_le(&key[8]));
  ascon_accel_write_reg(dev, ASCON_REG_KEY3, ascon_accel_load32_le(&key[12]));
}

void ascon_accel_write_nonce_128(const ascon_accel_t *dev, const uint8_t *nonce) {
  ascon_accel_write_reg(dev, ASCON_REG_NONCE0, ascon_accel_load32_le(&nonce[0]));
  ascon_accel_write_reg(dev, ASCON_REG_NONCE1, ascon_accel_load32_le(&nonce[4]));
  ascon_accel_write_reg(dev, ASCON_REG_NONCE2, ascon_accel_load32_le(&nonce[8]));
  ascon_accel_write_reg(dev, ASCON_REG_NONCE3, ascon_accel_load32_le(&nonce[12]));
}

void ascon_accel_read_tag_128(const ascon_accel_t *dev, uint8_t tag[16]) {
  ascon_accel_store32_le(&tag[0], ascon_accel_read_reg(dev, ASCON_REG_TAG0));
  ascon_accel_store32_le(&tag[4], ascon_accel_read_reg(dev, ASCON_REG_TAG1));
  ascon_accel_store32_le(&tag[8], ascon_accel_read_reg(dev, ASCON_REG_TAG2));
  ascon_accel_store32_le(&tag[12], ascon_accel_read_reg(dev, ASCON_REG_TAG3));
}

void ascon_accel_write_expected_tag_128(const ascon_accel_t *dev, const uint8_t tag[16]) {
  ascon_accel_write_reg(dev, ASCON_REG_TAG0, ascon_accel_load32_le(&tag[0]));
  ascon_accel_write_reg(dev, ASCON_REG_TAG1, ascon_accel_load32_le(&tag[4]));
  ascon_accel_write_reg(dev, ASCON_REG_TAG2, ascon_accel_load32_le(&tag[8]));
  ascon_accel_write_reg(dev, ASCON_REG_TAG3, ascon_accel_load32_le(&tag[12]));
}
