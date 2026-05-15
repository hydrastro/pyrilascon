#ifndef ASCON_ACCEL_H
#define ASCON_ACCEL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "ascon_accel_regs.h"

#ifndef ASCON_ACCEL_BASE_ADDR
#define ASCON_ACCEL_BASE_ADDR 0xFFEB0000u
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  ASCON_ACCEL_MODE_AEAD128 = ASCON_MODE_AEAD128,
  ASCON_ACCEL_MODE_AEAD128A = ASCON_MODE_AEAD128A,
  ASCON_ACCEL_MODE_AEAD128PQ = ASCON_MODE_AEAD128PQ,
  ASCON_ACCEL_MODE_HASH = ASCON_MODE_HASH,
  ASCON_ACCEL_MODE_HASHA = ASCON_MODE_HASHA,
  ASCON_ACCEL_MODE_XOF = ASCON_MODE_XOF,
  ASCON_ACCEL_MODE_XOFA = ASCON_MODE_XOFA,
  ASCON_ACCEL_MODE_CXOF128 = ASCON_MODE_CXOF128,
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
  ASCON_ACCEL_ERR_ABI_MISMATCH = -5,
  ASCON_ACCEL_ERR_HARDWARE_ERROR = -6,
  ASCON_ACCEL_ERR_TRANSPORT = -7,
} ascon_accel_status_t;

typedef enum {
  ASCON_ACCEL_DATA_PLANE_MMIO_WORD = 0,
  ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL = 1,
} ascon_accel_data_plane_t;

typedef enum {
  ASCON_ACCEL_STREAM_AD = ASCON_DATA_AD,
  ASCON_ACCEL_STREAM_TEXT = ASCON_DATA_TEXT,
  ASCON_ACCEL_STREAM_CUSTOM = ASCON_DATA_CUSTOM,
} ascon_accel_stream_kind_t;

typedef struct {
  void *ctx;
  ascon_accel_status_t (*send)(
      void *ctx,
      const uint8_t *data,
      size_t len,
      ascon_accel_stream_kind_t stream_kind);
  ascon_accel_status_t (*recv)(void *ctx, uint8_t *data, size_t len);
} ascon_accel_axis_transport_t;

typedef struct {
  uintptr_t base_addr;
  uint32_t timeout_cycles;
  ascon_accel_data_plane_t data_plane;
  ascon_accel_axis_transport_t axis_transport;
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
void ascon_accel_set_data_plane(ascon_accel_t *dev, ascon_accel_data_plane_t data_plane);
void ascon_accel_set_axis_transport(
    ascon_accel_t *dev,
    const ascon_accel_axis_transport_t *transport);
bool ascon_accel_axis_transport_configured(const ascon_accel_t *dev);
void ascon_accel_reset(const ascon_accel_t *dev);

uint32_t ascon_accel_abi_version(const ascon_accel_t *dev);
uint32_t ascon_accel_capabilities(const ascon_accel_t *dev);
uint32_t ascon_accel_error_code(const ascon_accel_t *dev);
uint64_t ascon_accel_cycle_count(const ascon_accel_t *dev);
bool ascon_accel_supports(const ascon_accel_t *dev, ascon_accel_mode_t mode);

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
