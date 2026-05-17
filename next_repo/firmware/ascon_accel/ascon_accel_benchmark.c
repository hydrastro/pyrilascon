#include "ascon_accel_benchmark.h"

static void populate_common(
    ascon_accel_benchmark_result_t *result,
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    ascon_accel_op_t operation,
    const ascon_accel_aead_request_t *req,
    ascon_accel_status_t status,
    uint64_t cycle_start,
    uint64_t cycle_end) {
  if (result == 0) {
    return;
  }
  result->status = status;
  result->mode = mode;
  result->operation = operation;
  result->ad_len = req == 0 ? 0u : req->ad_len;
  result->input_len = req == 0 ? 0u : req->input_len;
  result->cycle_start = cycle_start;
  result->cycle_end = cycle_end;
  result->elapsed_cycles = cycle_end >= cycle_start ? (cycle_end - cycle_start) : 0u;
  result->error_code = dev == 0 ? 0u : ascon_accel_error_code(dev);
  result->tag_valid = dev == 0 ? false : ascon_accel_tag_valid(dev);
}

void ascon_accel_benchmark_result_init(ascon_accel_benchmark_result_t *result) {
  if (result == 0) {
    return;
  }
  result->status = ASCON_ACCEL_ERR_BAD_ARGUMENT;
  result->mode = ASCON_ACCEL_MODE_AEAD128;
  result->operation = ASCON_ACCEL_OP_ENCRYPT;
  result->ad_len = 0u;
  result->input_len = 0u;
  result->cycle_start = 0u;
  result->cycle_end = 0u;
  result->elapsed_cycles = 0u;
  result->error_code = 0u;
  result->tag_valid = false;
}

ascon_accel_status_t ascon_accel_benchmark_encrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req,
    ascon_accel_benchmark_result_t *result) {
  uint64_t cycle_start = dev == 0 ? 0u : ascon_accel_cycle_count(dev);
  ascon_accel_status_t status = ascon_accel_encrypt(dev, mode, req);
  uint64_t cycle_end = dev == 0 ? 0u : ascon_accel_cycle_count(dev);
  populate_common(result, dev, mode, ASCON_ACCEL_OP_ENCRYPT, req, status, cycle_start, cycle_end);
  return status;
}

ascon_accel_status_t ascon_accel_benchmark_decrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req,
    ascon_accel_benchmark_result_t *result) {
  uint64_t cycle_start = dev == 0 ? 0u : ascon_accel_cycle_count(dev);
  ascon_accel_status_t status = ascon_accel_decrypt(dev, mode, req);
  uint64_t cycle_end = dev == 0 ? 0u : ascon_accel_cycle_count(dev);
  populate_common(result, dev, mode, ASCON_ACCEL_OP_DECRYPT, req, status, cycle_start, cycle_end);
  return status;
}

uint64_t ascon_accel_benchmark_mcycles_per_byte(
    const ascon_accel_benchmark_result_t *result) {
  if (result == 0 || result->input_len == 0u) {
    return 0u;
  }
  return (result->elapsed_cycles * 1000u) / (uint64_t)result->input_len;
}
