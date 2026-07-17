/* ---------------------------------------------------------------------------
 * SLINK data-plane self-test.
 *
 * Runs on the STREAM SoC (rtl/soc/neorv32_ascon_slink_soc.vhd) and answers three
 * questions on real hardware:
 *
 *   1. Is this actually the stream build?  (CAPABILITIES bit 23, and the SLINK +
 *      DMA blocks reporting themselves present)
 *   2. Does it compute correct Ascon?      (vectors below come from the Python
 *      model that passes the official NIST KATs -- not from the RTL)
 *   3. How fast is it?                     (the accelerator's own busy counter,
 *      the same metric the MMIO benchmark reports, so the numbers are directly
 *      comparable)
 *
 * Expected: every case PASS, and busy cycles far below the MMIO figures
 * (simulation says 118 vs 4948 for ad16_pt32).
 *
 * Build:  make -C firmware/ascon_slink_test FREESTANDING=1 exe
 * --------------------------------------------------------------------------- */
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include <neorv32.h>

#include "../ascon_slink/ascon_slink.h"

#define UART_BAUD 19200u
#define TIMEOUT   10000000u

static const uint8_t KEY[16]   = {0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f};
static const uint8_t NONCE[16] = {0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1a,0x1b,0x1c,0x1d,0x1e,0x1f};

typedef struct {
  const char *name;
  uint32_t    ad_len;
  uint32_t    msg_len;
  uint8_t     ad[32];
  uint8_t     msg[32];
  uint8_t     ct[32];
  uint8_t     tag[16];
} vec_t;

/* Generated from ascon_hwmodel (the NIST-KAT-validated model). */
static const vec_t VECTORS[] = {
  { "empty", 0, 0,
    {0},
    {0},
    {0},
    {0x4f,0x9c,0x27,0x82,0x11,0xbe,0xc9,0x31,0x6b,0xf6,0x8f,0x46,0xee,0x8b,0x2e,0xc6} },
  { "pt8", 0, 8,
    {0},
    {0x00,0x0b,0x16,0x21,0x2c,0x37,0x42,0x4d},
    {0xc8,0xe9,0xea,0xec,0x2c,0x7e,0xa1,0x80},
    {0x90,0x99,0x97,0xce,0xa2,0xc9,0x89,0xab,0xbe,0x8a,0xe8,0xe5,0x4a,0x88,0x9b,0x7f} },
  { "pt16", 0, 16,
    {0},
    {0x00,0x0b,0x16,0x21,0x2c,0x37,0x42,0x4d,0x58,0x63,0x6e,0x79,0x84,0x8f,0x9a,0xa5},
    {0xc8,0xe9,0xea,0xec,0x2c,0x7e,0xa1,0x80,0x93,0xa2,0x36,0x63,0x90,0x35,0x16,0x31},
    {0xbc,0xd9,0x04,0xb2,0x7f,0x42,0x77,0x42,0x69,0x96,0xc6,0xe2,0xd8,0x3c,0x5d,0x7c} },
  { "ad8_pt8", 8, 8,
    {0x00,0x07,0x0e,0x15,0x1c,0x23,0x2a,0x31},
    {0x00,0x0b,0x16,0x21,0x2c,0x37,0x42,0x4d},
    {0xf7,0x6d,0x99,0x48,0x31,0x40,0x1b,0x41},
    {0xf7,0x20,0x00,0x83,0xc3,0xe7,0x39,0xdf,0x76,0xda,0x39,0xe1,0x9e,0x4f,0x65,0xce} },
  { "pt32", 0, 32,
    {0},
    {0x00,0x0b,0x16,0x21,0x2c,0x37,0x42,0x4d,0x58,0x63,0x6e,0x79,0x84,0x8f,0x9a,0xa5,0xb0,0xbb,0xc6,0xd1,0xdc,0xe7,0xf2,0xfd,0x08,0x13,0x1e,0x29,0x34,0x3f,0x4a,0x55},
    {0xc8,0xe9,0xea,0xec,0x2c,0x7e,0xa1,0x80,0x93,0xa2,0x36,0x63,0x90,0x35,0x16,0x31,0xbd,0x36,0x76,0x78,0xb5,0xa0,0x37,0x75,0xa6,0x12,0x49,0x7a,0x33,0xb4,0x8f,0x08},
    {0xfb,0xc2,0x39,0x49,0x17,0xf5,0xbe,0x44,0x47,0xdb,0xd8,0x76,0xb2,0x30,0xbc,0xe1} },
  { "ad16_pt32", 16, 32,
    {0x00,0x07,0x0e,0x15,0x1c,0x23,0x2a,0x31,0x38,0x3f,0x46,0x4d,0x54,0x5b,0x62,0x69},
    {0x00,0x0b,0x16,0x21,0x2c,0x37,0x42,0x4d,0x58,0x63,0x6e,0x79,0x84,0x8f,0x9a,0xa5,0xb0,0xbb,0xc6,0xd1,0xdc,0xe7,0xf2,0xfd,0x08,0x13,0x1e,0x29,0x34,0x3f,0x4a,0x55},
    {0x0b,0xea,0x3b,0x79,0x8a,0xb5,0xc9,0x48,0xb2,0xc7,0x63,0xb5,0xe3,0x04,0x3e,0xe6,0x90,0x0a,0xda,0x1a,0x47,0x27,0x66,0x20,0x80,0x4d,0xdc,0x2c,0x04,0xa4,0x0e,0xfa},
    {0x5a,0x6f,0xc9,0x82,0xf0,0x89,0x20,0xed,0x85,0x3c,0xac,0xd7,0xe8,0x48,0x99,0x43} },
};
#define N_VEC (sizeof(VECTORS) / sizeof(VECTORS[0]))

static char nib(uint8_t n) { return (char)((n < 10u) ? (uint32_t)('0' + n) : (uint32_t)('a' + (n - 10u))); }

static void phex(const char *label, const uint8_t *d, uint32_t n) {
  neorv32_uart0_printf("%s", label);
  for (uint32_t i = 0u; i < n; ++i) neorv32_uart0_printf("%c%c", nib((uint8_t)(d[i] >> 4)), nib((uint8_t)(d[i] & 0xfu)));
  neorv32_uart0_printf("\n");
}

int main(void) {
  neorv32_rte_setup();
  neorv32_uart0_setup(UART_BAUD, 0);

  neorv32_uart0_printf("\n=== Ascon SLINK data-plane self-test ===\n");

  ascon_slink_t dev;
  ascon_slink_init(&dev, ASCON_SLINK_BASE_ADDR, TIMEOUT);

  const uint32_t caps = ascon_slink_capabilities(&dev);
  const uint32_t abi  = ascon_slink_abi(&dev);
  neorv32_uart0_printf("ABI          : 0x%x\n", abi);
  neorv32_uart0_printf("CAPABILITIES : 0x%x\n", caps);
  neorv32_uart0_printf("SLINK plane  : %s (cap bit 23)\n",
                       (caps & ASCON_SLINK_CAP_SLINK_PLANE) ? "YES" : "NO -- this is the MMIO bitstream!");
  neorv32_uart0_printf("SLINK block  : %s\n", neorv32_slink_available() ? "present" : "ABSENT");
  neorv32_uart0_printf("DMA block    : %s\n", neorv32_dma_available() ? "present" : "ABSENT");

  if (!(caps & ASCON_SLINK_CAP_SLINK_PLANE) || !ascon_slink_hw_ready()) {
    neorv32_uart0_printf("\nWrong bitstream or SLINK/DMA missing -- stopping.\n");
    while (1) {}
  }

  neorv32_uart0_printf("\n");
  uint32_t fails = 0u;

  for (uint32_t i = 0u; i < N_VEC; ++i) {
    const vec_t *v = &VECTORS[i];
    uint8_t out[32];
    memset(out, 0, sizeof(out));

    ascon_slink_request_t req;
    memset(&req, 0, sizeof(req));
    req.key = KEY; req.nonce = NONCE;
    req.ad = v->ad; req.ad_len = v->ad_len;
    req.input = v->msg; req.input_len = v->msg_len;
    req.output = out;

    const ascon_slink_status_t st = ascon_slink_encrypt(&dev, &req);
    const bool ct_ok  = (memcmp(out, v->ct, v->msg_len) == 0);
    const bool tag_ok = (memcmp(req.tag, v->tag, 16) == 0);
    const bool ok = (st == ASCON_SLINK_OK) && ct_ok && tag_ok;
    if (!ok) fails++;

    neorv32_uart0_printf("CASE %-10s ad=%2u pt=%2u  busy=%5u  ct=%s tag=%s  %s\n",
                         v->name, v->ad_len, v->msg_len, dev.last_busy_cycles,
                         ct_ok ? "ok" : "BAD", tag_ok ? "ok" : "BAD",
                         ok ? "PASS" : "FAIL");
    if (!ok) {
      neorv32_uart0_printf("  status=%d\n", (int)st);
      phex("  got ct : ", out, v->msg_len);
      phex("  exp ct : ", v->ct, v->msg_len);
      phex("  got tag: ", req.tag, 16u);
      phex("  exp tag: ", v->tag, 16u);
    }
  }

  /* Decrypt round-trip on the largest case, including the tag check. */
  {
    const vec_t *v = &VECTORS[N_VEC - 1u];
    uint8_t back[32];
    memset(back, 0, sizeof(back));
    ascon_slink_request_t req;
    memset(&req, 0, sizeof(req));
    req.key = KEY; req.nonce = NONCE;
    req.ad = v->ad; req.ad_len = v->ad_len;
    req.input = v->ct; req.input_len = v->msg_len;
    req.output = back;
    memcpy(req.tag, v->tag, 16);
    const ascon_slink_status_t st = ascon_slink_decrypt(&dev, &req);
    const bool ok = (st == ASCON_SLINK_OK) && (memcmp(back, v->msg, v->msg_len) == 0);
    if (!ok) fails++;
    neorv32_uart0_printf("DECRYPT %-8s busy=%5u  %s\n", v->name, dev.last_busy_cycles, ok ? "PASS" : "FAIL");

    /* Tamper: flip one ciphertext bit, expect the tag to reject it. */
    uint8_t bad[32];
    memcpy(bad, v->ct, v->msg_len);
    bad[0] ^= 0x01u;
    req.input = bad;
    memcpy(req.tag, v->tag, 16);
    const ascon_slink_status_t bst = ascon_slink_decrypt(&dev, &req);
    const bool caught = (bst == ASCON_SLINK_ERR_TAG_INVALID);
    if (!caught) fails++;
    neorv32_uart0_printf("TAMPER   1 bit flipped -> %s\n",
                         caught ? "REJECTED (correct)" : "ACCEPTED (WRONG!)");
  }

  neorv32_uart0_printf("\n%s: %u failure(s)\n", fails ? "FAIL" : "ALL PASS", fails);
  while (1) {}
  return 0;
}
