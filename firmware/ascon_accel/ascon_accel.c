#include "ascon_accel_internal.h"

/* Capability probing reads ASCON_REG_CAPABILITIES in ascon_accel_caps.c. */

static bool request_uses_mmio_data_plane(const ascon_accel_t *dev) {
  return dev->data_plane == ASCON_ACCEL_DATA_PLANE_MMIO_WORD;
}

static ascon_accel_status_t send_payload(
    const ascon_accel_t *dev,
    const uint8_t *data,
    size_t len,
    uint32_t stream_kind) {
  if (request_uses_mmio_data_plane(dev)) {
    ascon_accel_mmio_stream_bytes(dev, data, len, stream_kind);
    return ASCON_ACCEL_OK;
  }
  return ascon_accel_axis_stream_bytes(dev, data, len, stream_kind);
}

static ascon_accel_status_t recv_payload(const ascon_accel_t *dev, uint8_t *data, size_t len) {
  if (request_uses_mmio_data_plane(dev)) {
    ascon_accel_mmio_read_bytes(dev, data, len);
    return ASCON_ACCEL_OK;
  }
  return ascon_accel_axis_read_bytes(dev, data, len);
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
  if (!ascon_accel_is_valid_mode(mode) || !ascon_accel_supports(dev, mode) || !ascon_accel_is_aead_mode(mode)) {
    return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
  }

  ascon_accel_reset(dev);
  ascon_accel_write_reg(dev, ASCON_REG_MODE, (uint32_t)mode);
  ascon_accel_write_key_128(dev, req->key);
  ascon_accel_write_nonce_128(dev, req->nonce);
  ascon_accel_write_reg(dev, ASCON_REG_AD_LEN, (uint32_t)req->ad_len);
  ascon_accel_write_reg(dev, ASCON_REG_TEXT_LEN, (uint32_t)req->input_len);

  ascon_accel_status_t status = send_payload(dev, req->ad, req->ad_len, ASCON_DATA_AD);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  status = send_payload(dev, req->input, req->input_len, ASCON_DATA_TEXT);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }

  ascon_accel_write_reg(dev, ASCON_REG_CONTROL, ASCON_CONTROL_START);
  status = ascon_accel_wait_done(dev);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  status = recv_payload(dev, req->output, req->input_len);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  ascon_accel_read_tag_128(dev, (uint8_t *)req->tag);
  return ASCON_ACCEL_OK;
}

ascon_accel_status_t ascon_accel_decrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req) {
  if (dev == 0 || req == 0 || req->key == 0 || req->nonce == 0 || req->output == 0) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if ((req->ad_len != 0u && req->ad == 0) || (req->input_len != 0u && req->input == 0)) {
    return ASCON_ACCEL_ERR_BAD_ARGUMENT;
  }
  if (!ascon_accel_is_valid_mode(mode) || !ascon_accel_supports(dev, mode) || !ascon_accel_is_aead_mode(mode)) {
    return ASCON_ACCEL_ERR_UNSUPPORTED_MODE;
  }

  ascon_accel_reset(dev);
  ascon_accel_write_reg(dev, ASCON_REG_MODE, (uint32_t)mode);
  ascon_accel_write_key_128(dev, req->key);
  ascon_accel_write_nonce_128(dev, req->nonce);
  ascon_accel_write_reg(dev, ASCON_REG_AD_LEN, (uint32_t)req->ad_len);
  ascon_accel_write_reg(dev, ASCON_REG_TEXT_LEN, (uint32_t)req->input_len);
  ascon_accel_write_expected_tag_128(dev, req->tag);

  ascon_accel_status_t status = send_payload(dev, req->ad, req->ad_len, ASCON_DATA_AD);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  status = send_payload(dev, req->input, req->input_len, ASCON_DATA_TEXT);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }

  ascon_accel_write_reg(dev, ASCON_REG_CONTROL, ASCON_CONTROL_START | ASCON_CONTROL_DECRYPT);
  status = ascon_accel_wait_done(dev);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  if (!ascon_accel_tag_valid(dev)) {
    return ASCON_ACCEL_ERR_TAG_INVALID;
  }
  return recv_payload(dev, req->output, req->input_len);
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
  if (!ascon_accel_is_valid_mode(mode) || !ascon_accel_supports(dev, mode)) {
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
  ascon_accel_write_reg(dev, ASCON_REG_MODE, (uint32_t)mode);
  ascon_accel_write_reg(dev, ASCON_REG_TEXT_LEN, (uint32_t)req->message_len);
  ascon_accel_write_reg(dev, ASCON_REG_OUT_LEN, (uint32_t)req->output_len);
  ascon_accel_write_reg(dev, ASCON_REG_CUSTOM_LEN, (uint32_t)req->customization_len);
  if (mode == ASCON_ACCEL_MODE_CXOF128) {
    ascon_accel_status_t custom_status = send_payload(dev, req->customization, req->customization_len, ASCON_DATA_CUSTOM);
    if (custom_status != ASCON_ACCEL_OK) {
      return custom_status;
    }
  }
  ascon_accel_status_t message_status = send_payload(dev, req->message, req->message_len, ASCON_DATA_TEXT);
  if (message_status != ASCON_ACCEL_OK) {
    return message_status;
  }

  ascon_accel_write_reg(dev, ASCON_REG_CONTROL, control);
  ascon_accel_status_t status = ascon_accel_wait_done(dev);
  if (status != ASCON_ACCEL_OK) {
    return status;
  }
  return recv_payload(dev, req->output, req->output_len);
}
