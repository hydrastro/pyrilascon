#ifndef ASCON_ACCEL_AXIS_REF_EMULATOR_H
#define ASCON_ACCEL_AXIS_REF_EMULATOR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "ascon_accel.h"

#ifdef __cplusplus
extern "C" {
#endif

#ifndef ASCON_ACCEL_AXIS_REF_EMULATOR_MAX_BYTES
#define ASCON_ACCEL_AXIS_REF_EMULATOR_MAX_BYTES 4096u
#endif

/*
 * Host-side AXI Stream accelerator emulator.
 *
 * This transport is intentionally not a synthesizable model. It is a firmware
 * test harness that reads the same MMIO register image used by ascon_accel_t,
 * captures AXI Stream AD/text payloads, computes Ascon-AEAD128 with the
 * portable C reference implementation, and updates STATUS/TAG/ERROR/RX data as
 * the stream-native hardware top would.
 */
typedef struct {
  volatile uint32_t *regs;

  uint8_t ad[ASCON_ACCEL_AXIS_REF_EMULATOR_MAX_BYTES];
  uint8_t text[ASCON_ACCEL_AXIS_REF_EMULATOR_MAX_BYTES];
  uint8_t rx[ASCON_ACCEL_AXIS_REF_EMULATOR_MAX_BYTES];

  size_t ad_len;
  size_t text_len;
  size_t rx_len;
  size_t rx_offset;

  uint64_t cycle_counter;

  uint32_t send_calls;
  uint32_t recv_calls;
  uint32_t completed_operations;
  ascon_accel_stream_kind_t last_stream_kind;
  ascon_accel_status_t last_error;
  bool last_tag_valid;
} ascon_accel_axis_ref_emulator_ctx_t;

void ascon_accel_axis_ref_emulator_init(
    ascon_accel_axis_ref_emulator_ctx_t *ctx,
    volatile uint32_t *regs);

ascon_accel_axis_transport_t ascon_accel_axis_ref_emulator_transport(
    ascon_accel_axis_ref_emulator_ctx_t *ctx);

#ifdef __cplusplus
}
#endif

#endif
