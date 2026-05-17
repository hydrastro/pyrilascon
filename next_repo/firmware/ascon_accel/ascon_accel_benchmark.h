#ifndef ASCON_ACCEL_BENCHMARK_H
#define ASCON_ACCEL_BENCHMARK_H

#include <stddef.h>
#include <stdint.h>

#include "ascon_accel.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  ascon_accel_status_t status;
  ascon_accel_mode_t mode;
  ascon_accel_op_t operation;
  size_t ad_len;
  size_t input_len;
  uint64_t cycle_start;
  uint64_t cycle_end;
  uint64_t elapsed_cycles;
  uint32_t error_code;
  bool tag_valid;
} ascon_accel_benchmark_result_t;

void ascon_accel_benchmark_result_init(ascon_accel_benchmark_result_t *result);

ascon_accel_status_t ascon_accel_benchmark_encrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req,
    ascon_accel_benchmark_result_t *result);

ascon_accel_status_t ascon_accel_benchmark_decrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req,
    ascon_accel_benchmark_result_t *result);

uint64_t ascon_accel_benchmark_mcycles_per_byte(
    const ascon_accel_benchmark_result_t *result);

#ifdef __cplusplus
}
#endif

#endif
