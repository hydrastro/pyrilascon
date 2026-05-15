#ifndef ASCON_ACCEL_H
#define ASCON_ACCEL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifndef ASCON_ACCEL_BASE_ADDR
#define ASCON_ACCEL_BASE_ADDR 0xFFFFFF00u
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  ASCON_ACCEL_MODE_AEAD128 = 0,
  ASCON_ACCEL_MODE_AEAD128A = 1,
  ASCON_ACCEL_MODE_AEAD128PQ = 2,
  ASCON_ACCEL_MODE_HASH = 3,
  ASCON_ACCEL_MODE_HASHA = 4,
  ASCON_ACCEL_MODE_XOF = 5,
  ASCON_ACCEL_MODE_XOFA = 6,
  ASCON_ACCEL_MODE_CXOF128 = 7,
} ascon_accel_mode_t;

typedef enum {
  ASCON_ACCEL_OP_ENCRYPT = 0,
  ASCON_ACCEL_OP_DECRYPT = 1,
  ASCON_ACCEL_OP_HASH = 2,
  ASCON_ACCEL_OP_XOF = 3,
  ASCON_ACCEL_OP_CXOF = 4,
} ascon_accel_op_t;

typedef enum {
  ASCON_ACCEL_OK = 0,
  ASCON_ACCEL_ERR_BAD_ARGUMENT = -1,
  ASCON_ACCEL_ERR_TIMEOUT = -2,
  ASCON_ACCEL_ERR_TAG_INVALID = -3,
  ASCON_ACCEL_ERR_UNSUPPORTED_MODE = -4,
} ascon_accel_status_t;

typedef struct {
  uintptr_t base_addr;
  uint32_t timeout_cycles;
} ascon_accel_t;

typedef struct {
  const uint8_t *key;
  const uint8_t *nonce;
  const uint8_t *ad;
  size_t ad_len;
  const uint8_t *input;
  size_t input_len;
  uint8_t *output;
  uint8_t tag[16];
} ascon_accel_aead_request_t;

typedef struct {
  const uint8_t *message;
  size_t message_len;
  const uint8_t *customization;
  size_t customization_len;
  uint8_t *output;
  size_t output_len;
} ascon_accel_hash_request_t;

void ascon_accel_init(ascon_accel_t *dev, uintptr_t base_addr, uint32_t timeout_cycles);
void ascon_accel_reset(const ascon_accel_t *dev);
bool ascon_accel_busy(const ascon_accel_t *dev);
bool ascon_accel_done(const ascon_accel_t *dev);
bool ascon_accel_tag_valid(const ascon_accel_t *dev);

ascon_accel_status_t ascon_accel_encrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req);

ascon_accel_status_t ascon_accel_decrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req);

ascon_accel_status_t ascon_accel_hash_or_xof(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_hash_request_t *req);

#ifdef __cplusplus
}
#endif

#endif
