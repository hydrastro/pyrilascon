/* ---------------------------------------------------------------------------
 * SLINK data-plane benchmark -- the same sweep as the MMIO benchmark, over the
 * stream data plane, emitting the identical CASE line format so that
 * host/ascon_bench.py parses it unchanged and the two runs are directly
 * comparable.
 *
 * Runs on the STREAM SoC only (make soc-build-slink). On the MMIO bitstream it
 * reports CAPABILITIES bit 23 clear and stops, rather than producing nonsense.
 *
 * The comparison is the same one the project has always made: the C reference
 * and the accelerator on one CPU, one clock, one fabric, one counter.
 *
 *   sw_*_cy : rdcycle64() either side of the reference C call
 *   hw_*_cy : the accelerator's CYCLE_COUNT register (reset each op, so it is
 *             the elapsed START->DONE busy time)
 *
 * Build:  make -C firmware/ascon_slink_bench FREESTANDING=1 exe
 * --------------------------------------------------------------------------- */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include <neorv32.h>

#include "../ascon_slink/ascon_slink.h"
#include "../ascon_ref/ascon_ref_aead128.h"

#define UART_BAUD      19200u
#define ACCEL_TIMEOUT  10000000u
#define MAX_BYTES      32u

static uint64_t rdcycle64(void) {
#if __riscv_xlen == 64
  uint64_t v; __asm__ volatile ("rdcycle %0" : "=r"(v)); return v;
#else
  uint32_t hi0, lo, hi1;
  do {
    __asm__ volatile ("rdcycleh %0" : "=r"(hi0));
    __asm__ volatile ("rdcycle  %0" : "=r"(lo));
    __asm__ volatile ("rdcycleh %0" : "=r"(hi1));
  } while (hi0 != hi1);
  return ((uint64_t)hi1 << 32) | (uint64_t)lo;
#endif
}

typedef struct { const char *name; uint32_t ad_len; uint32_t pt_len; } bench_case_t;

/* Identical sweep to the MMIO benchmark, so the tables line up row for row. */
static const bench_case_t CASES[] = {
  { "empty",     0u,  0u },
  { "ad8",       8u,  0u },
  { "pt8",       0u,  8u },
  { "ad8_pt8",   8u,  8u },
  { "pt16",      0u, 16u },
  { "pt24",      0u, 24u },
  { "pt32",      0u, 32u },
  { "ad16_pt32",16u, 32u },
};
#define N_CASES (sizeof(CASES) / sizeof(CASES[0]))

static const uint8_t KEY[16] = {
  0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f };
static const uint8_t NONCE[16] = {
  0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1a,0x1b,0x1c,0x1d,0x1e,0x1f };

static uint8_t ad_pool[MAX_BYTES];
static uint8_t pt_pool[MAX_BYTES];

static bool bytes_equal(const uint8_t *a, const uint8_t *b, size_t n) {
  for (size_t i = 0u; i < n; ++i) if (a[i] != b[i]) return false;
  return true;
}

static bool run_case(ascon_slink_t *dev, const bench_case_t *c) {
  uint8_t sw_ct[MAX_BYTES], sw_tag[16], sw_pt[MAX_BYTES];
  uint8_t hw_ct[MAX_BYTES], hw_pt[MAX_BYTES];
  bool sw_valid = false;

  /* ---- software reference, both directions, timed ---- */
  const uint64_t t0 = rdcycle64();
  const int sw_e = ascon_ref_aead128_encrypt(KEY, NONCE, ad_pool, c->ad_len,
                                             pt_pool, c->pt_len, sw_ct, sw_tag);
  const uint64_t t1 = rdcycle64();
  const int sw_d = ascon_ref_aead128_decrypt(KEY, NONCE, ad_pool, c->ad_len,
                                             sw_ct, c->pt_len, sw_tag, sw_pt, &sw_valid);
  const uint64_t t2 = rdcycle64();
  const uint64_t sw_enc_cy = t1 - t0;
  const uint64_t sw_dec_cy = t2 - t1;

  if (sw_e != 0 || sw_d != 0 || !sw_valid) {
    neorv32_uart0_printf("CASE name=%s SW_ERR\n", c->name);
    return false;
  }

  /* ---- hardware encrypt over the stream plane ---- */
  ascon_slink_request_t req;
  memset(&req, 0, sizeof(req));
  req.key = KEY; req.nonce = NONCE;
  req.ad = ad_pool; req.ad_len = c->ad_len;
  req.input = pt_pool; req.input_len = c->pt_len;
  req.output = hw_ct;
  const ascon_slink_status_t est = ascon_slink_encrypt(dev, &req);
  const uint32_t hw_enc_cy = dev->last_busy_cycles;
  uint8_t hw_tag[16];
  memcpy(hw_tag, req.tag, 16);

  const bool enc_ok = (est == ASCON_SLINK_OK) &&
                      bytes_equal(hw_ct, sw_ct, c->pt_len) &&
                      bytes_equal(hw_tag, sw_tag, 16u);

  /* ---- hardware decrypt (round-trip + tag check) ---- */
  memset(&req, 0, sizeof(req));
  req.key = KEY; req.nonce = NONCE;
  req.ad = ad_pool; req.ad_len = c->ad_len;
  req.input = hw_ct; req.input_len = c->pt_len;
  req.output = hw_pt;
  memcpy(req.tag, hw_tag, 16);
  const ascon_slink_status_t dst = ascon_slink_decrypt(dev, &req);
  const uint32_t hw_dec_cy = dev->last_busy_cycles;

  const bool dec_ok = (dst == ASCON_SLINK_OK) && bytes_equal(hw_pt, pt_pool, c->pt_len);
  const bool tag_valid = (dst == ASCON_SLINK_OK);

  neorv32_uart0_printf(
      "CASE name=%s ad=%u pt=%u "
      "sw_enc_cy=%u:%u sw_dec_cy=%u:%u "
      "hw_enc_cy=%u:%u hw_dec_cy=%u:%u "
      "enc_ok=%u dec_ok=%u tag_valid=%u "
      "hw_enc_err=0x%x hw_dec_err=0x%x\n",
      c->name, c->ad_len, c->pt_len,
      (uint32_t)(sw_enc_cy >> 32), (uint32_t)(sw_enc_cy & 0xffffffffu),
      (uint32_t)(sw_dec_cy >> 32), (uint32_t)(sw_dec_cy & 0xffffffffu),
      0u, hw_enc_cy,
      0u, hw_dec_cy,
      enc_ok ? 1u : 0u, dec_ok ? 1u : 0u, tag_valid ? 1u : 0u,
      (est == ASCON_SLINK_OK) ? 0u : (uint32_t)(-est),
      (dst == ASCON_SLINK_OK) ? 0u : (uint32_t)(-dst));

  return enc_ok && dec_ok;
}

int main(void) {
  neorv32_rte_setup();
  neorv32_uart0_setup(UART_BAUD, 0);

  for (uint32_t i = 0u; i < MAX_BYTES; ++i) {
    ad_pool[i] = (uint8_t)(0x60u + i);
    pt_pool[i] = (uint8_t)(0xA0u + i);
  }

  ascon_slink_t dev;
  ascon_slink_init(&dev, ASCON_SLINK_BASE_ADDR, ACCEL_TIMEOUT);
  const uint32_t caps = ascon_slink_capabilities(&dev);

  neorv32_uart0_printf("\npyrilascon NEORV32 ASCON benchmark\n");
  neorv32_uart0_printf("BUILD        : cosim-neorv32-slink\n");
  neorv32_uart0_printf("MAX_BYTES    : %u\n", MAX_BYTES);
  neorv32_uart0_printf("SWEEP_CASES  : %u\n", (uint32_t)N_CASES);
  neorv32_uart0_printf("DATA PLANE   : SLINK_DMA_STREAM\n");
  neorv32_uart0_printf("ABI          : 0x%x\n", ascon_slink_abi(&dev));
  neorv32_uart0_printf("CAPS         : 0x%x\n", caps);

  if (!(caps & ASCON_SLINK_CAP_SLINK_PLANE)) {
    neorv32_uart0_printf("\nThis is the MMIO bitstream (CAPS bit 23 clear).\n");
    neorv32_uart0_printf("Build and flash the stream SoC: make soc-build-slink soc-flash-slink\n");
    while (1) {}
  }
  if (!ascon_slink_hw_ready()) {
    neorv32_uart0_printf("\nSLINK=%d DMA=%d -- SoC lacks IO_SLINK_EN/IO_DMA_EN.\n",
                         neorv32_slink_available(), neorv32_dma_available());
    while (1) {}
  }

  uint32_t passed = 0u, failed = 0u;
  for (uint32_t i = 0u; i < N_CASES; ++i) {
    if (run_case(&dev, &CASES[i])) passed++; else failed++;
  }

  neorv32_uart0_printf("SUMMARY      : passed=%u failed=%u total=%u\n",
                       passed, failed, (uint32_t)N_CASES);
  neorv32_uart0_printf("%s\n", failed ? "FAIL" : "PASS");
  while (1) {}
  return 0;
}
