#ifndef ASCON_ACCEL_INTERNAL_H
#define ASCON_ACCEL_INTERNAL_H

#include "ascon_accel.h"

#ifdef __cplusplus
extern "C" {
#endif

volatile uint32_t *ascon_accel_reg(const ascon_accel_t *dev, uint32_t offset);
void ascon_accel_write_reg(const ascon_accel_t *dev, uint32_t offset, uint32_t value);
uint32_t ascon_accel_read_reg(const ascon_accel_t *dev, uint32_t offset);

uint32_t ascon_accel_load32_le(const uint8_t *p);
void ascon_accel_store32_le(uint8_t *p, uint32_t x);

bool ascon_accel_is_valid_mode(ascon_accel_mode_t mode);
bool ascon_accel_is_aead_mode(ascon_accel_mode_t mode);
uint32_t ascon_accel_capability_bit_for_mode(ascon_accel_mode_t mode);
ascon_accel_status_t ascon_accel_wait_done(const ascon_accel_t *dev);

void ascon_accel_write_key_128(const ascon_accel_t *dev, const uint8_t *key);
void ascon_accel_write_nonce_128(const ascon_accel_t *dev, const uint8_t *nonce);
void ascon_accel_read_tag_128(const ascon_accel_t *dev, uint8_t tag[16]);
void ascon_accel_write_expected_tag_128(const ascon_accel_t *dev, const uint8_t tag[16]);

void ascon_accel_mmio_stream_bytes(
    const ascon_accel_t *dev,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t stream_kind);
void ascon_accel_mmio_read_bytes(const ascon_accel_t *dev, uint8_t *data, size_t len);

ascon_accel_status_t ascon_accel_axis_stream_bytes(
    const ascon_accel_t *dev,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t stream_kind);
ascon_accel_status_t ascon_accel_axis_read_bytes(const ascon_accel_t *dev, uint8_t *data, size_t len);

#ifdef __cplusplus
}
#endif

#endif
