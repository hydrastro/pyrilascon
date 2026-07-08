#include "ascon_accel_internal.h"

bool ascon_accel_is_valid_mode(ascon_accel_mode_t mode) {
  switch (mode) {
    case ASCON_ACCEL_MODE_AEAD128:
    case ASCON_ACCEL_MODE_AEAD128A:
    case ASCON_ACCEL_MODE_AEAD128PQ:
    case ASCON_ACCEL_MODE_HASH:
    case ASCON_ACCEL_MODE_HASHA:
    case ASCON_ACCEL_MODE_XOF:
    case ASCON_ACCEL_MODE_XOFA:
    case ASCON_ACCEL_MODE_CXOF128:
      return true;
    default:
      return false;
  }
}

uint32_t ascon_accel_capability_bit_for_mode(ascon_accel_mode_t mode) {
  switch (mode) {
    case ASCON_ACCEL_MODE_AEAD128:
      return ASCON_CAP_AEAD128;
    case ASCON_ACCEL_MODE_AEAD128A:
      return ASCON_CAP_AEAD128A;
    case ASCON_ACCEL_MODE_AEAD128PQ:
      return ASCON_CAP_AEAD128PQ;
    case ASCON_ACCEL_MODE_HASH:
      return ASCON_CAP_HASH;
    case ASCON_ACCEL_MODE_HASHA:
      return ASCON_CAP_HASHA;
    case ASCON_ACCEL_MODE_XOF:
      return ASCON_CAP_XOF;
    case ASCON_ACCEL_MODE_XOFA:
      return ASCON_CAP_XOFA;
    case ASCON_ACCEL_MODE_CXOF128:
      return ASCON_CAP_CXOF128;
    default:
      return 0u;
  }
}

bool ascon_accel_is_aead_mode(ascon_accel_mode_t mode) {
  return mode == ASCON_ACCEL_MODE_AEAD128 ||
         mode == ASCON_ACCEL_MODE_AEAD128A ||
         mode == ASCON_ACCEL_MODE_AEAD128PQ;
}

uint32_t ascon_accel_abi_version(const ascon_accel_t *dev) {
  return ascon_accel_read_reg(dev, ASCON_REG_ABI_VERSION);
}

uint32_t ascon_accel_capabilities(const ascon_accel_t *dev) {
  return ascon_accel_read_reg(dev, ASCON_REG_CAPABILITIES);
}

bool ascon_accel_supports(const ascon_accel_t *dev, ascon_accel_mode_t mode) {
  uint32_t cap = ascon_accel_capability_bit_for_mode(mode);
  if (dev == 0 || cap == 0u) {
    return false;
  }
  return (ascon_accel_capabilities(dev) & cap) != 0u;
}
