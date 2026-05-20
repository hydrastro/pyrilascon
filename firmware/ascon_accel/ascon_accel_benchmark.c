#include "ascon_accel_benchmark.h"

/*
 * Rationale for the elapsed-cycles computation
 * --------------------------------------------
 * The hardware's CYCLE_COUNT register is *not* a free-running clock counter.
 * It is reset to zero on every CONTROL.CLEAR write (see
 * ascon_accel_mmio_regs.v) and increments only while core_busy_i is asserted.
 *
 * The driver's ascon_accel_encrypt() and ascon_accel_decrypt() entry points
 * both call ascon_accel_reset() at the very start of the operation, which
 * writes CONTROL.CLEAR. As a result, after the operation finishes the
 * counter holds exactly the number of cycles the hardware was busy during
 * the operation: that is itself the elapsed-cycles value.
 *
 * A previous version of this wrapper computed (cycle_end - cycle_start),
 * which produced 0 for the second operation in a benchmark run (the reset
 * inside the operation zeroed the counter mid-way through the measurement
 * window, so cycle_end < cycle_start and the saturating subtraction folded
 * to 0). The fix is to read the counter once, after the operation, and
 * treat that value as the elapsed cycle count.
 *
 * cycle_start is still recorded for diagnostic purposes but no longer
 * participates in the elapsed-cycles arithmetic.
 */

static void populate_common(
    ascon_accel_benchmark_result_t *result,
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    ascon_accel_op_t operation,
    const ascon_accel_aead_request_t *req,
    ascon_accel_status_t status,
    uint64_t cycle_start,
    uint64_t cycle_end) {
  if (result == NULL) {
    return;
  }
  result->status = status;
  result->mode = mode;
  result->operation = operation;
  result->ad_len = (req == NULL) ? (size_t)0 : req->ad_len;
  result->input_len = (req == NULL) ? (size_t)0 : req->input_len;
  result->cycle_start = cycle_start;
  result->cycle_end = cycle_end;
  /* See rationale at top of file: the CYCLE_COUNT register IS the
     elapsed-cycles value because it is reset at the start of each op. */
  result->elapsed_cycles = cycle_end;
  result->error_code = (dev == NULL) ? 0u : ascon_accel_error_code(dev);
  result->tag_valid = (dev == NULL) ? false : ascon_accel_tag_valid(dev);
}

void ascon_accel_benchmark_result_init(ascon_accel_benchmark_result_t *result) {
  if (result == NULL) {
    return;
  }
  result->status = ASCON_ACCEL_ERR_BAD_ARGUMENT;
  result->mode = ASCON_ACCEL_MODE_AEAD128;
  result->operation = ASCON_ACCEL_OP_ENCRYPT;
  result->ad_len = (size_t)0;
  result->input_len = (size_t)0;
  result->cycle_start = (uint64_t)0;
  result->cycle_end = (uint64_t)0;
  result->elapsed_cycles = (uint64_t)0;
  result->error_code = 0u;
  result->tag_valid = false;
}

ascon_accel_status_t ascon_accel_benchmark_encrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req,
    ascon_accel_benchmark_result_t *result) {
  uint64_t cycle_start = (dev == NULL) ? (uint64_t)0 : ascon_accel_cycle_count(dev);
  ascon_accel_status_t status = ascon_accel_encrypt(dev, mode, req);
  uint64_t cycle_end = (dev == NULL) ? (uint64_t)0 : ascon_accel_cycle_count(dev);
  populate_common(result, dev, mode, ASCON_ACCEL_OP_ENCRYPT, req, status, cycle_start, cycle_end);
  return status;
}

ascon_accel_status_t ascon_accel_benchmark_decrypt(
    const ascon_accel_t *dev,
    ascon_accel_mode_t mode,
    const ascon_accel_aead_request_t *req,
    ascon_accel_benchmark_result_t *result) {
  uint64_t cycle_start = (dev == NULL) ? (uint64_t)0 : ascon_accel_cycle_count(dev);
  ascon_accel_status_t status = ascon_accel_decrypt(dev, mode, req);
  uint64_t cycle_end = (dev == NULL) ? (uint64_t)0 : ascon_accel_cycle_count(dev);
  populate_common(result, dev, mode, ASCON_ACCEL_OP_DECRYPT, req, status, cycle_start, cycle_end);
  return status;
}

uint64_t ascon_accel_benchmark_mcycles_per_byte(
    const ascon_accel_benchmark_result_t *result) {
  if (result == NULL || result->input_len == (size_t)0) {
    return (uint64_t)0;
  }
  return (result->elapsed_cycles * (uint64_t)1000) / (uint64_t)result->input_len;
}
