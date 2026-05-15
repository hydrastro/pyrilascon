#include "ascon_accel.h"

static volatile uint32_t *ascon_reg(const ascon_accel_t *dev, uint32_t offset) {
  return (volatile uint32_t *)(dev->base_addr + (uintptr_t)offset);
}

static void write_reg(const ascon_accel_t *dev, uint32_t offset, uint32_t value) {
  *ascon_reg(dev, offset) = value;
}

static uint32_t read_reg(const ascon_accel_t *dev, uint32_t offset) {
  return *ascon_reg(dev, offset);
}

static uint32_t load32_le(const uint8_t *p) {
  return ((uint32_t)p[0]) |
         ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}

static void store32_le(uint8_t *p, uint32_t x) {
  p[0] = (uint8_t)(x & 0xffu);
  p[1] = (uint8_t)((x >> 8) & 0xffu);
  p[2] = (uint8_t)((x >> 16) & 0xffu);
  p[3] = (uint8_t)((x >> 24) & 0xffu);
}

static bool is_valid_mode(ascon_accel_mode_t mode) {
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

static uint32_t capability_bit_for_mode(ascon_accel_mode_t mode) {
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

static bool is_aead_mode(ascon_accel_mode_t mode) {
  return mode == ASCON_ACCEL_MODE_AEAD128 ||
         mode == ASCON_ACCEL_MODE_AEAD128A ||
         mode == ASCON_ACCEL_MODE_AEAD128PQ;
}

static ascon_accel_status_t wait_done(const ascon_accel_t *dev) {
  uint32_t timeout = dev->timeout_cycles;
  while (timeout-- != 0u) {
    uint32_t status = read_reg(dev, ASCON_REG_STATUS);
    if ((status & ASCON_STATUS_ERROR) != 0u) {
      return ASCON_ACCEL_ERR_HARDWARE_ERROR;
    }
    if ((status & ASCON_STATUS_DONE) != 0u) {
      return ASCON_ACCEL_OK;
    }
  }
  return ASCON_ACCEL_ERR_TIMEOUT;
}

static void write_key_128(const ascon_accel_t *dev, const uint8_t *key) {
  write_reg(dev, ASCON_REG_KEY0, load32_le(&key[0]));
  write_reg(dev, ASCON_REG_KEY1, load32_le(&key[4]));
  write_reg(dev, ASCON_REG_KEY2, load32_le(&key[8]));
  write_reg(dev, ASCON_REG_KEY3, load32_le(&key[12]));
}

static void write_nonce_128(const ascon_accel_t *dev, const uint8_t *nonce) {
  write_reg(dev, ASCON_REG_NONCE0, load32_le(&nonce[0]));
  write_reg(dev, ASCON_REG_NONCE1, load32_le(&nonce[4]));
  write_reg(dev, ASCON_REG_NONCE2, load32_le(&nonce[8]));
  write_reg(dev, ASCON_REG_NONCE3, load32_le(&nonce[12]));
}

static void read_tag_128(const ascon_accel_t *dev, uint8_t tag[16]) {
  store32_le(&tag[0], read_reg(dev, ASCON_REG_TAG0));
  store32_le(&tag[4], read_reg(dev, ASCON_REG_TAG1));
  store32_le(&tag[8], read_reg(dev, ASCON_REG_TAG2));
  store32_le(&tag[12], read_reg(dev, ASCON_REG_TAG3));
}

static void stream_bytes(const ascon_accel_t *dev, const uint8_t *data, size_t len, uint32_t stream_kind) {
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
    uint32_t ctrl = ASCON_DATA_VALID | stream_kind | (keep << 8);
    if (offset == len) {
      ctrl |= ASCON_DATA_LAST;
    }
    write_reg(dev, ASCON_REG_DATA_IN, word);
    write_reg(dev, ASCON_REG_DATA_IN_CTRL, ctrl);
  }
  if (len == 0u) {
    write_reg(dev, ASCON_REG_DATA_IN, 0u);
    write_reg(dev, ASCON_REG_DATA_IN_CTRL, ASCON_DATA_VALID | ASCON_DATA_LAST | stream_kind);
  }
}

static void read_bytes(const ascon_accel_t *dev, uint8_t *data, size_t len) {
  size_t offset = 0;
  while (offset < len) {
    uint32_t word = read_reg(dev, ASCON_REG_DATA_OUT);
    for (uint32_t i = 0; i < 4u && offset < len; ++i) {
      data[offset++] = (uint8_t)((word >> (8u * i)) & 0xffu);
    }
    (void)read_reg(dev, ASCON_REG_DATA_OUT_CTRL);
  }
}

void ascon_accel_init(ascon_accel_t *dev, uintptr_t base_addr, uint32_t timeout_cycles) {
  if (dev == 0) {
    return;
  }
  dev->base_addr = base_addr;
  dev->timeout_cycles = timeout_cycles;
}

void ascon_accel_reset(const ascon_accel_t *dev) {
  write_reg(dev, ASCON_REG_CONTROL, ASCON_CONTROL_CLEAR);
}

uint32_t ascon_accel_abi_version(const ascon_accel_t *dev) {
  return read_reg(dev, ASCON_REG_ABI_VERSION);
}

uint32_t ascon_accel_capabilities(const ascon_accel_t *dev) {
  return read_reg(dev, ASCON_REG_CAPABILITIES);
}

uint32_t ascon_accel_error_code(const ascon_accel_t *dev) {
  return read_reg(dev, ASCON_REG_ERROR_CODE);
}

uint64_t ascon_accel_cycle_count(const ascon_accel_t *dev) {
  uint32_t hi0;
  uint32_t lo;
  uint32_t hi1;
  do {
    hi0 = read_reg(dev, ASCON_REG_CYCLE_COUNT_HI);
    lo = read_reg(dev, ASCON_REG_CYCLE_COUNT_LO);
    hi1 = read_reg(dev, ASCON_REG_CYCLE_COUNT_HI);
  } while (hi0 != hi1);
  return ((uint64_t)hi1 << 32) | (uint64_t)lo;
}

bool ascon_accel_supports(const ascon_accel_t *dev, ascon_accel_mode_t mode) {
  uint32_t cap = capability_bit_for_mode(mode);
  if (dev == 0 || cap == 0u) {
    return false;
  }
  return (ascon_accel_capabilities(dev) & cap) != 0u;
}

bool ascon_accel_busy(const ascon_accel_t *dev) {
  return (read_reg(dev, ASCON_REG_STATUS) & ASCON_STATUS_BUSY) != 0u;
}

bool ascon_accel_done(const ascon_accel_t *dev) {
  return (read_reg(dev, ASCON_REG_STATUS) & ASCON_STATUS_DONE) != 0u;
}

bool ascon_accel_tag_valid(const ascon_accel_t *dev) {
  return (read_reg(dev, ASCON_REG_STATUS) & ASCON_STATUS_TAG_VALID) != 0u;
}

ascon_accel_status_t ascon_accel_encrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req) {
  if (dev == 0 || req == 0 || req->key == 0 || req->nonce == 0 || req->output == 0) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if ((req->ad_len != 0u && req->ad == 0) || (req->input_len != 0u && req->input == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if ((req->ad_len != 0u && req->ad == 0) || (req->input_len != 0u && req->input == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (!is_valid_mode(mode) || !ascon_accel_supports(dev, mode) || !is_aead_mode(mode)) {
    return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
  }

  ascon_accel_reset(dev);
  write_reg(dev, ASCON_REG_MODE, (uint32_t)mode);
  write_key_128(dev, req->key);
  write_nonce_128(dev, req->nonce);
  write_reg(dev, ASCON_REG_AD_LEN, (uint32_t)req->ad_len);
  write_reg(dev, ASCON_REG_TEXT_LEN, (uint32_t)req->input_len);
  stream_bytes(dev, req->ad, req->ad_len, ASCON_DATA_AD);
  stream_bytes(dev, req->input, req->input_len, ASCON_DATA_TEXT);
  write_reg(dev, ASCON_REG_CONTROL, ASCON_CONTROL_START);

  ascon_accel_status_t status = wait_done(dev);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  read_bytes(dev, req->output, req->input_len);
  read_tag_128(dev, (uint8_t *)req->tag);
  return ASCON_ACCEL_OK;
}

ascon_accel_status_t ascon_accel_decrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req) {
  if (dev == 0 || req == 0 || req->key == 0 || req->nonce == 0 || req->output == 0) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (!is_valid_mode(mode) || !ascon_accel_supports(dev, mode) || !is_aead_mode(mode)) {
    return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
  }

  ascon_accel_reset(dev);
  write_reg(dev, ASCON_REG_MODE, (uint32_t)mode);
  write_key_128(dev, req->key);
  write_nonce_128(dev, req->nonce);
  write_reg(dev, ASCON_REG_AD_LEN, (uint32_t)req->ad_len);
  write_reg(dev, ASCON_REG_TEXT_LEN, (uint32_t)req->input_len);
  write_reg(dev, ASCON_REG_TAG0, load32_le(&req->tag[0]));
  write_reg(dev, ASCON_REG_TAG1, load32_le(&req->tag[4]));
  write_reg(dev, ASCON_REG_TAG2, load32_le(&req->tag[8]));
  write_reg(dev, ASCON_REG_TAG3, load32_le(&req->tag[12]));
  stream_bytes(dev, req->ad, req->ad_len, ASCON_DATA_AD);
  stream_bytes(dev, req->input, req->input_len, ASCON_DATA_TEXT);
  write_reg(dev, ASCON_REG_CONTROL, ASCON_CONTROL_START | ASCON_CONTROL_DECRYPT);

  ascon_accel_status_t status = wait_done(dev);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  if (!ascon_accel_tag_valid(dev)) {
    return ASCON_ACCEL_ERR_TAG_INVALID;
  }
  read_bytes(dev, req->output, req->input_len);
  return ASCON_ACCEL_OK;
}

ascon_accel_status_t ascon_accel_hash_or_xof(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_hash_request_t *req) {
  if (dev == 0 || req == 0 || req->output == 0) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if ((req->message_len != 0u && req->message == 0) ||
      (req->customization_len != 0u && req->customization == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (!is_valid_mode(mode) || !ascon_accel_supports(dev, mode)) {
    return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
  }

  uint32_t control = ASCON_CONTROL_START;
  if (mode == ASCON_ACCEL_MODE_HASH || mode == ASCON_ACCEL_MODE_HASHA) {
    control |= ASCON_CONTROL_HASH;
  } else if (mode == ASCON_ACCEL_MODE_XOF || mode == ASCON_ACCEL_MODE_XOFA) {
    control |= ASCON_CONTROL_XOF;
  } else if (mode == ASCON_ACCEL_MODE_CXOF128) {
    control |= ASCON_CONTROL_CXOF;
  } else {
    return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
  }

  ascon_accel_reset(dev);
  write_reg(dev, ASCON_REG_MODE, (uint32_t)mode);
  write_reg(dev, ASCON_REG_TEXT_LEN, (uint32_t)req->message_len);
  write_reg(dev, ASCON_REG_OUT_LEN, (uint32_t)req->output_len);
  write_reg(dev, ASCON_REG_CUSTOM_LEN, (uint32_t)req->customization_len);
  if (mode == ASCON_ACCEL_MODE_CXOF128) {
    stream_bytes(dev, req->customization, req->customization_len, ASCON_DATA_CUSTOM);
  }
  stream_bytes(dev, req->message, req->message_len, ASCON_DATA_TEXT);
  write_reg(dev, ASCON_REG_CONTROL, control);

  ascon_accel_status_t status = wait_done(dev);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  read_bytes(dev, req->output, req->output_len);
  return ASCON_ACCEL_OK;
}
