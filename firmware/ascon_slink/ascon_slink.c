/* ---------------------------------------------------------------------------
 * ascon_slink -- driver for the stream-data-plane Ascon accelerator.
 *
 * The contrast with firmware/ascon_accel is the whole point of the design:
 *
 *   MMIO path    : the CPU writes DATA_IN + DATA_IN_CTRL for every 4 bytes.
 *                  Two bus transactions per word; measured 4948 accelerator
 *                  busy cycles for 16 B AD + 32 B message, of which 98% was the
 *                  accelerator waiting for the CPU.
 *
 *   SLINK path   : the CPU writes key/nonce/lengths/START, programs a DMA
 *                  descriptor, and waits. The DMA reads DMEM and writes the
 *                  SLINK TX register with a *constant* destination address; SLINK
 *                  presents it as AXI4-Stream; the accelerator consumes a beat
 *                  per cycle. Same case: 118 busy cycles in simulation.
 *
 * The CPU never touches a payload byte.
 *
 * Stream contract (see rtl/soc/ascon_slink_shim.v): send ceil(AD_LEN/4) words of
 * associated data, then ceil(MSG_LEN/4) words of message. The shim derives
 * tuser/tkeep/tlast from the AD_LEN/TEXT_LEN registers, so the payload is a
 * plain word stream -- which is exactly what a DMA can produce.
 *
 * IMPORTANT -- FIFO sizing. NEORV32's SLINK does not back-pressure bus writes:
 * a write to a full TX FIFO is lost. The DMA can therefore only run unthrottled
 * if the TX FIFO is at least as deep as the largest payload in words
 * (32 B AD + 32 B message = 16 words). The SoC sets IO_SLINK_TX_FIFO => 16 for
 * exactly this reason. Raising AD_MAX/MSG_MAX means raising the FIFO too, or
 * throttling the DMA into chunks.
 * --------------------------------------------------------------------------- */
#include "ascon_slink.h"

#include <neorv32.h>

/* Control-plane register offsets (see rtl/soc/ascon_aead128_slink_mmio.v). */
#define A_CONTROL 0x00u
#define A_STATUS  0x04u
#define A_MODE    0x08u
#define A_CAPS    0x0Cu
#define A_ADLEN   0x10u
#define A_TXTLEN  0x14u
#define A_KEY0    0x20u
#define A_NON0    0x30u
#define A_TAG0    0x60u
#define A_CYCLO   0x70u
#define A_CYCHI   0x74u
#define A_ERR     0x78u
#define A_ABI     0x7Cu

#define CTRL_START   0x1u
#define CTRL_DECRYPT 0x2u
#define CTRL_CLEAR   0x100u

#define ST_BUSY 0x1u
#define ST_DONE 0x2u
#define ST_TAGV 0x4u
#define ST_ERR  0x8u

static volatile uint32_t *reg(uintptr_t base, uint32_t off) {
  return (volatile uint32_t *)(base + (uintptr_t)off);
}

static uint32_t load_le32(const uint8_t *p, size_t avail) {
  uint32_t w = 0u;
  for (size_t i = 0u; i < 4u && i < avail; ++i) {
    w |= ((uint32_t)p[i]) << (8u * i);
  }
  return w;
}

static void store_le32(uint8_t *p, size_t avail, uint32_t w) {
  for (size_t i = 0u; i < 4u && i < avail; ++i) {
    p[i] = (uint8_t)((w >> (8u * i)) & 0xffu);
  }
}

static size_t words_for(size_t bytes) { return (bytes + 3u) / 4u; }

void ascon_slink_init(ascon_slink_t *dev, uintptr_t base, uint32_t timeout_cycles) {
  dev->base = base;
  dev->timeout_cycles = timeout_cycles;
  dev->last_busy_cycles = 0u;
}

uint32_t ascon_slink_capabilities(const ascon_slink_t *dev) {
  return *reg(dev->base, A_CAPS);
}

uint32_t ascon_slink_abi(const ascon_slink_t *dev) {
  return *reg(dev->base, A_ABI);
}

int ascon_slink_hw_ready(void) {
  return neorv32_slink_available() && neorv32_dma_available();
}

/* Push `nwords` words from `src` into the SLINK TX register using the DMA.
 * Source increments through memory; destination is the single TX data register.
 * This is the line that removes the CPU from the payload path. */
static ascon_slink_status_t dma_to_slink(const uint32_t *src, size_t nwords,
                                         uint32_t timeout) {
  if (nwords == 0u) return ASCON_SLINK_OK;

  neorv32_dma_program((uint32_t)(uintptr_t)src,
                      (uint32_t)(uintptr_t)&NEORV32_SLINK->DATA,
                      (uint32_t)nwords | DMA_SRC_INC_WORD | DMA_DST_CONST_WORD);
  neorv32_dma_start();

  for (uint32_t i = 0u; i < timeout; ++i) {
    if (neorv32_dma_status() == DMA_STATUS_DONE) return ASCON_SLINK_OK;
  }
  return ASCON_SLINK_ERR_TIMEOUT;
}

/* Pull `nwords` words out of the SLINK RX register into memory using the DMA. */
static ascon_slink_status_t dma_from_slink(uint32_t *dst, size_t nwords,
                                           uint32_t timeout) {
  if (nwords == 0u) return ASCON_SLINK_OK;

  neorv32_dma_program((uint32_t)(uintptr_t)&NEORV32_SLINK->DATA,
                      (uint32_t)(uintptr_t)dst,
                      (uint32_t)nwords | DMA_SRC_CONST_WORD | DMA_DST_INC_WORD);
  neorv32_dma_start();

  for (uint32_t i = 0u; i < timeout; ++i) {
    if (neorv32_dma_status() == DMA_STATUS_DONE) return ASCON_SLINK_OK;
  }
  return ASCON_SLINK_ERR_TIMEOUT;
}

static ascon_slink_status_t run(ascon_slink_t *dev,
                                const ascon_slink_request_t *req,
                                int decrypt) {
  if (dev == 0 || req == 0) return ASCON_SLINK_ERR_BAD_ARGUMENT;
  if (req->ad_len > ASCON_SLINK_AD_MAX || req->input_len > ASCON_SLINK_MSG_MAX) {
    return ASCON_SLINK_ERR_BAD_ARGUMENT;
  }
  if (!ascon_slink_hw_ready()) return ASCON_SLINK_ERR_UNSUPPORTED;

  /* Word-align the payload once, into a scratch buffer the DMA can walk.
   * The shim masks the surplus bytes of the final AD word with tkeep, so the
   * padding is never absorbed into the sponge. */
  uint32_t txbuf[(ASCON_SLINK_AD_MAX / 4u) + (ASCON_SLINK_MSG_MAX / 4u)];
  size_t nw = 0u;
  for (size_t off = 0u; off < req->ad_len; off += 4u) {
    txbuf[nw++] = load_le32(&req->ad[off], req->ad_len - off);
  }
  for (size_t off = 0u; off < req->input_len; off += 4u) {
    txbuf[nw++] = load_le32(&req->input[off], req->input_len - off);
  }

  neorv32_slink_setup(0);        /* no interrupts: we poll */
  neorv32_dma_enable();

  /* ---- control plane: a handful of register writes ---- */
  *reg(dev->base, A_CONTROL) = CTRL_CLEAR;
  *reg(dev->base, A_MODE)    = 0u;
  for (uint32_t i = 0u; i < 4u; ++i) {
    *reg(dev->base, A_KEY0 + 4u * i) = load_le32(&req->key[4u * i], 4u);
    *reg(dev->base, A_NON0 + 4u * i) = load_le32(&req->nonce[4u * i], 4u);
  }
  if (decrypt) {
    for (uint32_t i = 0u; i < 4u; ++i) {
      *reg(dev->base, A_TAG0 + 4u * i) = load_le32(&req->tag[4u * i], 4u);
    }
  }
  *reg(dev->base, A_ADLEN)  = (uint32_t)req->ad_len;
  *reg(dev->base, A_TXTLEN) = (uint32_t)req->input_len;

  /* START before streaming: the engine must be in its receive state, asserting
   * tready, before the first beat arrives. (This ordering is the same one that
   * cost a day of board bring-up on the MMIO path.) */
  *reg(dev->base, A_CONTROL) = CTRL_START | (decrypt ? CTRL_DECRYPT : 0u);

  /* ---- payload plane: the CPU is now a spectator ---- */
  ascon_slink_status_t st = dma_to_slink(txbuf, nw, dev->timeout_cycles);
  if (st != ASCON_SLINK_OK) return st;

  /* ---- wait for the engine ---- */
  uint32_t status = 0u;
  uint32_t guard = 0u;
  while (((status = *reg(dev->base, A_STATUS)) & ST_DONE) == 0u) {
    if (++guard > dev->timeout_cycles) return ASCON_SLINK_ERR_TIMEOUT;
  }
  dev->last_busy_cycles = *reg(dev->base, A_CYCLO);

  /* ---- collect the result off the RX stream ---- */
  if (req->input_len > 0u && req->output != 0) {
    uint32_t rxbuf[ASCON_SLINK_MSG_MAX / 4u];
    const size_t rn = words_for(req->input_len);
    st = dma_from_slink(rxbuf, rn, dev->timeout_cycles);
    if (st != ASCON_SLINK_OK) return st;
    for (size_t i = 0u; i < rn; ++i) {
      store_le32(&req->output[4u * i], req->input_len - 4u * i, rxbuf[i]);
    }
  }

  /* ---- tag ---- */
  if (!decrypt) {
    for (uint32_t i = 0u; i < 4u; ++i) {
      store_le32(&((uint8_t *)req->tag)[4u * i], 4u, *reg(dev->base, A_TAG0 + 4u * i));
    }
  } else if ((status & ST_TAGV) == 0u) {
    return ASCON_SLINK_ERR_TAG_INVALID;
  }

  if (status & ST_ERR) return ASCON_SLINK_ERR_HARDWARE;
  return ASCON_SLINK_OK;
}

ascon_slink_status_t ascon_slink_encrypt(ascon_slink_t *dev, ascon_slink_request_t *req) {
  return run(dev, req, 0);
}

ascon_slink_status_t ascon_slink_decrypt(ascon_slink_t *dev, ascon_slink_request_t *req) {
  return run(dev, req, 1);
}
