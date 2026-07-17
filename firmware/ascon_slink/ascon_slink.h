/* ---------------------------------------------------------------------------
 * ascon_slink.h -- driver for the stream-data-plane Ascon-AEAD128 accelerator.
 *
 * Control travels over the CPU bus; the payload travels over AXI4-Stream, moved
 * by the DMA. See ascon_slink.c for the reasoning and the FIFO-sizing rule.
 *
 * Build the matching SoC with rtl/soc/neorv32_ascon_slink_soc.vhd.
 * --------------------------------------------------------------------------- */
#ifndef ASCON_SLINK_H
#define ASCON_SLINK_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Must match the AD_MAX / MSG_MAX generics on ascon_aead128_slink_wb, and the
 * SLINK TX FIFO must be at least (AD_MAX + MSG_MAX)/4 words deep. */
#define ASCON_SLINK_AD_MAX  32u
#define ASCON_SLINK_MSG_MAX 32u

/* Same base address as the MMIO accelerator: XBUS, outside the CPU core. */
#define ASCON_SLINK_BASE_ADDR 0x90000000u

/* CAPABILITIES bits. Bit 23 is what distinguishes this build from the MMIO one. */
#define ASCON_SLINK_CAP_AEAD128       (1u << 0)
#define ASCON_SLINK_CAP_CYCLE_COUNTER (1u << 21)
#define ASCON_SLINK_CAP_AXI_STREAM    (1u << 22)
#define ASCON_SLINK_CAP_SLINK_PLANE   (1u << 23)

typedef enum {
  ASCON_SLINK_OK = 0,
  ASCON_SLINK_ERR_BAD_ARGUMENT = -1,
  ASCON_SLINK_ERR_TIMEOUT = -2,
  ASCON_SLINK_ERR_TAG_INVALID = -3,
  ASCON_SLINK_ERR_UNSUPPORTED = -4,
  ASCON_SLINK_ERR_HARDWARE = -6
} ascon_slink_status_t;

typedef struct {
  uintptr_t base;
  uint32_t  timeout_cycles;
  uint32_t  last_busy_cycles;   /* accelerator START->DONE, from its own counter */
} ascon_slink_t;

typedef struct {
  const uint8_t *key;      /* 16 bytes */
  const uint8_t *nonce;    /* 16 bytes */
  const uint8_t *ad;
  size_t         ad_len;
  const uint8_t *input;
  size_t         input_len;
  uint8_t       *output;
  uint8_t        tag[16];  /* out on encrypt, in on decrypt */
} ascon_slink_request_t;

void     ascon_slink_init(ascon_slink_t *dev, uintptr_t base, uint32_t timeout_cycles);
uint32_t ascon_slink_capabilities(const ascon_slink_t *dev);
uint32_t ascon_slink_abi(const ascon_slink_t *dev);

/* True only if the SoC was built with IO_SLINK_EN and IO_DMA_EN. */
int      ascon_slink_hw_ready(void);

ascon_slink_status_t ascon_slink_encrypt(ascon_slink_t *dev, ascon_slink_request_t *req);
ascon_slink_status_t ascon_slink_decrypt(ascon_slink_t *dev, ascon_slink_request_t *req);

#ifdef __cplusplus
}
#endif

#endif /* ASCON_SLINK_H */
