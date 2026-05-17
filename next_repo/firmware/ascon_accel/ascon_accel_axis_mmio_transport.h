#ifndef ASCON_ACCEL_AXIS_MMIO_TRANSPORT_H
#define ASCON_ACCEL_AXIS_MMIO_TRANSPORT_H

#include <stddef.h>
#include <stdint.h>

#include "ascon_accel.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Minimal CPU-driven memory-mapped AXI-stream bridge register block.
 *
 * This is a firmware transport for small NEORV32/bring-up systems where the
 * CPU manually pushes/pulls 128-bit stream beats instead of using DMA.  The
 * register block is intentionally separate from the frozen ASCON accelerator
 * CSR map: ASCON_ACCEL_BASE_ADDR still points at the control/status ABI, while
 * this transport base points at a stream bridge connected to the stream-native
 * backend's s_axis/m_axis ports.
 */
#ifndef ASCON_ACCEL_AXIS_MMIO_BASE_ADDR
#define ASCON_ACCEL_AXIS_MMIO_BASE_ADDR 0xFFEC0000u
#endif

#define ASCON_AXIS_MMIO_DATA_BYTES 16u
#define ASCON_AXIS_MMIO_KEEP_FULL  0xFFFFu

/* Byte offsets from the stream bridge base address. */
#define ASCON_AXIS_MMIO_TX_DATA0   0x00u
#define ASCON_AXIS_MMIO_TX_DATA1   0x04u
#define ASCON_AXIS_MMIO_TX_DATA2   0x08u
#define ASCON_AXIS_MMIO_TX_DATA3   0x0Cu
#define ASCON_AXIS_MMIO_TX_KEEP    0x10u
#define ASCON_AXIS_MMIO_TX_USER    0x14u
#define ASCON_AXIS_MMIO_TX_CTRL    0x18u
#define ASCON_AXIS_MMIO_STATUS     0x1Cu
#define ASCON_AXIS_MMIO_RX_DATA0   0x20u
#define ASCON_AXIS_MMIO_RX_DATA1   0x24u
#define ASCON_AXIS_MMIO_RX_DATA2   0x28u
#define ASCON_AXIS_MMIO_RX_DATA3   0x2Cu
#define ASCON_AXIS_MMIO_RX_KEEP    0x30u
#define ASCON_AXIS_MMIO_RX_USER    0x34u
#define ASCON_AXIS_MMIO_RX_CTRL    0x38u

#define ASCON_AXIS_MMIO_TX_CTRL_VALID  (1u << 0)
#define ASCON_AXIS_MMIO_TX_CTRL_LAST   (1u << 1)

#define ASCON_AXIS_MMIO_STATUS_TX_READY (1u << 0)
#define ASCON_AXIS_MMIO_STATUS_RX_VALID (1u << 1)
#define ASCON_AXIS_MMIO_STATUS_RX_LAST  (1u << 2)
#define ASCON_AXIS_MMIO_STATUS_RX_LEVEL_SHIFT 8u
#define ASCON_AXIS_MMIO_STATUS_RX_LEVEL_MASK  (0xffu << ASCON_AXIS_MMIO_STATUS_RX_LEVEL_SHIFT)
#define ASCON_AXIS_MMIO_STATUS_ERROR    (1u << 31)

#define ASCON_AXIS_MMIO_RX_CTRL_POP     (1u << 0)

typedef struct {
  uintptr_t base_addr;
  uint32_t timeout_cycles;
  uint32_t beats_sent;
  uint32_t beats_received;
  ascon_accel_status_t last_error;
} ascon_accel_axis_mmio_transport_ctx_t;

void ascon_accel_axis_mmio_transport_init(
    ascon_accel_axis_mmio_transport_ctx_t *ctx,
    uintptr_t base_addr,
    uint32_t timeout_cycles);

ascon_accel_axis_transport_t ascon_accel_axis_mmio_transport(
    ascon_accel_axis_mmio_transport_ctx_t *ctx);

#ifdef __cplusplus
}
#endif

#endif
