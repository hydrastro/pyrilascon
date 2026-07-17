/* ---------------------------------------------------------------------------
 * Ascon-AEAD128 live demo -- STREAM (SLINK + DMA) data plane.
 *
 * Same script as firmware/ascon_demo, but over the AXI4-Stream data plane, so it
 * runs on the stream SoC (rtl/soc/neorv32_ascon_slink_soc.vhd). On the MMIO
 * bitstream it says so and stops rather than timing out.
 *
 * It reports BOTH numbers, and on this data plane the distinction is the whole
 * story:
 *
 *   HW busy  -- the accelerator's START->DONE counter. On the stream plane the
 *               DMA runs *inside* this window, so the DMA's cost is counted.
 *   HW wall  -- rdcycle around the entire driver call: descriptor setup, the
 *               transfer, the wait, and the read-back.
 *
 * Build:  make -C firmware/ascon_slink_demo FREESTANDING=1 exe
 * --------------------------------------------------------------------------- */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include <neorv32.h>

#include "../ascon_slink/ascon_slink.h"
#include "../ascon_ref/ascon_ref_aead128.h"

#define UART_BAUD     19200u
#define ACCEL_TIMEOUT 10000000u
#define MAX_BYTES     32u

static const char    MESSAGE[] = "Politecnico di Milano";
static const uint8_t AD[]      = { 0x68,0x65,0x61,0x64,0x65,0x72,0x30,0x31 };
static const uint8_t KEY[16]   = {
  0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f };
static const uint8_t NONCE[16] = {
  0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1a,0x1b,0x1c,0x1d,0x1e,0x1f };

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

static char nib(uint8_t n) {
  return (char)((n < 10u) ? (uint32_t)('0' + n) : (uint32_t)('a' + (n - 10u)));
}

static void print_hex(const char *label, const uint8_t *d, uint32_t n) {
  neorv32_uart0_printf("%s", label);
  for (uint32_t i = 0u; i < n; ++i)
    neorv32_uart0_printf("%c%c", nib((uint8_t)(d[i] >> 4)), nib((uint8_t)(d[i] & 0xfu)));
  neorv32_uart0_printf("\n");
}

static void print_text(const char *label, const uint8_t *d, uint32_t n) {
  neorv32_uart0_printf("%s\"", label);
  for (uint32_t i = 0u; i < n; ++i) neorv32_uart0_printf("%c", (char)d[i]);
  neorv32_uart0_printf("\"\n");
}

int main(void) {
  neorv32_rte_setup();
  neorv32_uart0_setup(UART_BAUD, 0);

  const uint32_t msg_len = (uint32_t)(sizeof(MESSAGE) - 1u);
  uint8_t ct[MAX_BYTES], pt_back[MAX_BYTES], sw_ct[MAX_BYTES], sw_tag[16];

  neorv32_uart0_printf("\n=================================================\n");
  neorv32_uart0_printf(" Ascon-AEAD128 accelerator -- live demo (STREAM)\n");
  neorv32_uart0_printf(" NEORV32 RISC-V SoC @ 27 MHz  /  Tang Nano 20K\n");
  neorv32_uart0_printf("=================================================\n\n");

  ascon_slink_t dev;
  ascon_slink_init(&dev, ASCON_SLINK_BASE_ADDR, ACCEL_TIMEOUT);
  const uint32_t caps = ascon_slink_capabilities(&dev);

  neorv32_uart0_printf("[1] Accelerator found at 0x%x\n", (uint32_t)ASCON_SLINK_BASE_ADDR);
  neorv32_uart0_printf("    ABI          : 0x%x\n", ascon_slink_abi(&dev));
  neorv32_uart0_printf("    CAPABILITIES : 0x%x", caps);
  neorv32_uart0_printf("   (bit0=AEAD128, bit21=cycles, bit23=SLINK plane)\n");
  neorv32_uart0_printf("    DATA PLANE   : AXI4-Stream via SLINK, moved by DMA\n\n");

  if (!(caps & ASCON_SLINK_CAP_SLINK_PLANE)) {
    neorv32_uart0_printf("This is the MMIO bitstream -- run firmware/ascon_demo instead,\n");
    neorv32_uart0_printf("or flash the stream SoC: make soc-build-slink soc-flash-slink\n");
    while (1) {}
  }
  if (!ascon_slink_hw_ready()) {
    neorv32_uart0_printf("SLINK=%d DMA=%d -- SoC lacks IO_SLINK_EN / IO_DMA_EN.\n",
                         neorv32_slink_available(), neorv32_dma_available());
    while (1) {}
  }

  print_text("[2] Plaintext        : ", (const uint8_t *)MESSAGE, msg_len);
  print_hex ("    Associated data  : ", AD, (uint32_t)sizeof(AD));
  print_hex ("    Key              : ", KEY, 16u);
  print_hex ("    Nonce            : ", NONCE, 16u);
  neorv32_uart0_printf("\n");

  /* ---- 3. Hardware encrypt, over the stream ---- */
  ascon_slink_request_t enc;
  memset(&enc, 0, sizeof(enc));
  enc.key = KEY; enc.nonce = NONCE;
  enc.ad = AD; enc.ad_len = sizeof(AD);
  enc.input = (const uint8_t *)MESSAGE; enc.input_len = msg_len;
  enc.output = ct;

  const uint64_t hw_t0 = rdcycle64();
  const ascon_slink_status_t est = ascon_slink_encrypt(&dev, &enc);
  const uint64_t hw_t1 = rdcycle64();

  if (est != ASCON_SLINK_OK) {
    neorv32_uart0_printf("[3] HW encrypt FAILED status=%d\n", (int)est);
    while (1) {}
  }
  const uint32_t hw_busy = dev.last_busy_cycles;
  const uint32_t hw_wall = (uint32_t)(hw_t1 - hw_t0);

  neorv32_uart0_printf("[3] Hardware encrypt (payload never touched by the CPU)\n");
  print_hex("    Ciphertext       : ", ct, msg_len);
  print_hex("    Tag              : ", enc.tag, 16u);
  neorv32_uart0_printf("    HW busy cycles   : %u   (START->DONE; the DMA runs inside this)\n", hw_busy);
  neorv32_uart0_printf("    HW wall cycles   : %u   (incl. descriptor setup + readback)\n\n", hw_wall);

  /* ---- 4. Software reference on the same CPU ---- */
  const uint64_t sw_t0 = rdcycle64();
  const int sw_rc = ascon_ref_aead128_encrypt(KEY, NONCE, AD, sizeof(AD),
                                              (const uint8_t *)MESSAGE, msg_len,
                                              sw_ct, sw_tag);
  const uint64_t sw_t1 = rdcycle64();
  const uint32_t sw_cy = (uint32_t)(sw_t1 - sw_t0);

  const bool same = (sw_rc == 0) && (memcmp(ct, sw_ct, msg_len) == 0) &&
                    (memcmp(enc.tag, sw_tag, 16) == 0);

  neorv32_uart0_printf("[4] Software (reference C) on the same CPU\n");
  neorv32_uart0_printf("    SW cycles        : %u\n", sw_cy);
  neorv32_uart0_printf("    Identical result : %s\n", same ? "YES" : "NO");
  if (hw_busy) {
    const uint32_t s = (sw_cy * 10u) / hw_busy;
    neorv32_uart0_printf("    Speed-up (engine): %u.%ux   [SW / HW busy]\n", s / 10u, s % 10u);
  }
  if (hw_wall) {
    const uint32_t s = (sw_cy * 10u) / hw_wall;
    neorv32_uart0_printf("    Speed-up (wall)  : %u.%ux   [SW / HW end-to-end]\n\n", s / 10u, s % 10u);
  }

  /* ---- 5. Hardware decrypt ---- */
  ascon_slink_request_t dec;
  memset(&dec, 0, sizeof(dec));
  dec.key = KEY; dec.nonce = NONCE;
  dec.ad = AD; dec.ad_len = sizeof(AD);
  dec.input = ct; dec.input_len = msg_len;
  dec.output = pt_back;
  memcpy(dec.tag, enc.tag, 16);

  const ascon_slink_status_t dst = ascon_slink_decrypt(&dev, &dec);
  neorv32_uart0_printf("[5] Hardware decrypt\n");
  if (dst == ASCON_SLINK_OK) {
    print_text("    Recovered        : ", pt_back, msg_len);
    neorv32_uart0_printf("    Tag valid        : YES\n");
    neorv32_uart0_printf("    Round-trip       : %s\n\n",
                         (memcmp(pt_back, MESSAGE, msg_len) == 0) ? "MESSAGE RECOVERED" : "MISMATCH");
  } else {
    neorv32_uart0_printf("    FAILED status=%d\n\n", (int)dst);
  }

  /* ---- 6. Tamper test ---- */
  uint8_t bad[MAX_BYTES];
  memcpy(bad, ct, msg_len);
  bad[0] ^= 0x01u;

  ascon_slink_request_t tam;
  memset(&tam, 0, sizeof(tam));
  tam.key = KEY; tam.nonce = NONCE;
  tam.ad = AD; tam.ad_len = sizeof(AD);
  tam.input = bad; tam.input_len = msg_len;
  tam.output = pt_back;
  memcpy(tam.tag, enc.tag, 16);

  const ascon_slink_status_t tst = ascon_slink_decrypt(&dev, &tam);
  neorv32_uart0_printf("[6] Tamper test -- flipping ONE bit of the ciphertext\n");
  print_hex("    Tampered ct      : ", bad, msg_len);
  neorv32_uart0_printf("    Tag valid        : %s",
                       (tst == ASCON_SLINK_ERR_TAG_INVALID) ? "NO" : "YES");
  neorv32_uart0_printf("    %s\n",
                       (tst == ASCON_SLINK_ERR_TAG_INVALID)
                         ? "<-- tampering detected by the hardware"
                         : "<-- NOT DETECTED (wrong!)");
  neorv32_uart0_printf("    Driver status    : %d   (%s)\n\n", (int)tst,
                       (tst == ASCON_SLINK_ERR_TAG_INVALID) ? "ERR_TAG_INVALID" : "unexpected");

  neorv32_uart0_printf("=================================================\n");
  neorv32_uart0_printf(" Demo complete.\n");
  neorv32_uart0_printf("=================================================\n");
  while (1) {}
  return 0;
}
