#ifndef ASCON_ACCEL_AXIS_DMA_TRANSPORT_H
#define ASCON_ACCEL_AXIS_DMA_TRANSPORT_H

#include <stddef.h>
#include <stdint.h>

#include "ascon_accel.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Descriptor-driven AXI-stream DMA front-end (data plane only).
 *
 * This is the autonomous counterpart of ascon_accel_axis_mmio_transport.  The
 * MMIO transport makes the CPU push and pop every 128-bit beat, so a long
 * payload costs O(length) loads and stores.  This DMA front-end instead takes a
 * small descriptor -- source addresses, lengths, and a destination address --
 * and then moves the whole encryption payload itself: it fetches the associated
 * data and plaintext from memory, feeds the stream-native backend, drains the
 * ciphertext beats, and writes them back to the destination buffer.  The CPU
 * only programs five descriptor registers and one GO bit, then waits for DONE
 * (or an interrupt).
 *
 * The register block is separate from the frozen ASCON CSR map.  The control
 * plane (key/nonce/lengths/CONTROL.START and the resulting tag) is still driven
 * through the normal ascon_accel CSR API at ASCON_ACCEL_BASE_ADDR; this base
 * points at the DMA descriptor block wired in front of the backend's stream
 * ports.  The autonomous path automates *encryption* only; buffered
 * authenticated decryption keeps the CPU-driven transport.
 *
 * Addresses programmed into the descriptor are the addresses seen by the DMA's
 * memory master port.  On the NEORV32 bring-up SoC that is the physical address
 * of the buffer; the words are 32-bit, little-endian, 4-byte aligned.
 */
#ifndef ASCON_ACCEL_AXIS_DMA_BASE_ADDR
#define ASCON_ACCEL_AXIS_DMA_BASE_ADDR 0xFFED0000u
#endif

#define ASCON_AXIS_DMA_DATA_BYTES 16u

/* Byte offsets from the DMA descriptor base address. */
#define ASCON_AXIS_DMA_AD_ADDR    0x00u
#define ASCON_AXIS_DMA_AD_LEN     0x04u
#define ASCON_AXIS_DMA_TEXT_ADDR  0x08u
#define ASCON_AXIS_DMA_TEXT_LEN   0x0Cu
#define ASCON_AXIS_DMA_DST_ADDR   0x10u
#define ASCON_AXIS_DMA_CTRL       0x14u
#define ASCON_AXIS_DMA_STATUS     0x18u
#define ASCON_AXIS_DMA_OUT_BYTES  0x1Cu

#define ASCON_AXIS_DMA_CTRL_GO      (1u << 0)
#define ASCON_AXIS_DMA_CTRL_IRQ_EN  (1u << 8)
#define ASCON_AXIS_DMA_CTRL_CLEAR   (1u << 16)

#define ASCON_AXIS_DMA_STATUS_BUSY  (1u << 0)
#define ASCON_AXIS_DMA_STATUS_DONE  (1u << 1)
#define ASCON_AXIS_DMA_STATUS_ERROR (1u << 2)
#define ASCON_AXIS_DMA_STATUS_OUT_BEATS_SHIFT 8u
#define ASCON_AXIS_DMA_STATUS_OUT_BEATS_MASK  (0xffu << ASCON_AXIS_DMA_STATUS_OUT_BEATS_SHIFT)

typedef struct {
  uintptr_t base_addr;
  uint32_t timeout_cycles;
  int irq_enabled;
  uint32_t last_status;
  uint32_t last_out_bytes;
  ascon_accel_status_t last_error;
} ascon_accel_axis_dma_ctx_t;

/* A single autonomous encryption transfer (descriptor contents). */
typedef struct {
  uintptr_t ad_addr;    /* source address of associated data       */
  size_t ad_len;        /* associated-data length in bytes         */
  uintptr_t text_addr;  /* source address of the plaintext         */
  size_t text_len;      /* plaintext length in bytes               */
  uintptr_t dst_addr;   /* destination address for the ciphertext  */
} ascon_accel_axis_dma_descriptor_t;

/* Initialise the DMA context.  irq_enabled selects polling (0) or IRQ (1). */
void ascon_accel_axis_dma_init(
    ascon_accel_axis_dma_ctx_t *ctx,
    uintptr_t base_addr,
    uint32_t timeout_cycles,
    int irq_enabled);

/* Clear any latched DONE/ERROR state from a previous transfer. */
void ascon_accel_axis_dma_clear(ascon_accel_axis_dma_ctx_t *ctx);

/* Program the descriptor registers without setting GO. */
ascon_accel_status_t ascon_accel_axis_dma_program(
    ascon_accel_axis_dma_ctx_t *ctx,
    const ascon_accel_axis_dma_descriptor_t *desc);

/* Pulse CTRL.GO to launch a previously programmed descriptor. */
void ascon_accel_axis_dma_start(ascon_accel_axis_dma_ctx_t *ctx);

/* Poll STATUS until DONE/ERROR or the timeout elapses. */
ascon_accel_status_t ascon_accel_axis_dma_wait_done(ascon_accel_axis_dma_ctx_t *ctx);

/*
 * Convenience one-shot: clear, program, start, and wait.  The frozen CSR
 * control plane (key/nonce/lengths/mode + CONTROL.START) must already have been
 * programmed via the ascon_accel CSR API before this call, exactly as the
 * cosim testbench sequences it.  On success, *out_bytes (if non-NULL) receives
 * the number of ciphertext bytes the DMA wrote to dst_addr.
 */
ascon_accel_status_t ascon_accel_axis_dma_run(
    ascon_accel_axis_dma_ctx_t *ctx,
    const ascon_accel_axis_dma_descriptor_t *desc,
    size_t *out_bytes);

#ifdef __cplusplus
}
#endif

#endif
