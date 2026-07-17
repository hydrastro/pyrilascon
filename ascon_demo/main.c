/* ---------------------------------------------------------------------------
 * Ascon-AEAD128 accelerator -- live demonstration firmware
 *
 * A short, human-readable demo intended to be run in front of an audience.
 * It performs, on the real accelerator at 0x9000_0000:
 *
 *   1. identifies the hardware (ABI + capability register),
 *   2. encrypts a readable message and prints ciphertext + tag,
 *   3. runs the same operation in reference software on the same CPU and
 *      reports the measured cycle counts and the speed-up,
 *   4. decrypts on the hardware and shows the message coming back,
 *   5. flips a single bit of the ciphertext and shows the tag check FAIL.
 *
 * Step 5 is the point of authenticated encryption: the tag detects tampering.
 *
 * Build (inside `nix develop`):
 *     make -C firmware/ascon_demo FREESTANDING=1 exe
 * Upload:
 *     python host/neorv32_upload.py <serial-port> firmware/ascon_demo/neorv32_exe.bin demo.log
 * --------------------------------------------------------------------------- */
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include <neorv32.h>

#include "../ascon_accel/ascon_accel.h"
#include "../ascon_ref/ascon_ref_aead128.h"

#define UART_BAUD            19200u
#define ACCEL_TIMEOUT_CYCLES 10000000u

/* The MMIO backend is bounded to 32 bytes of AD and 32 bytes of message. */
#define MAX_BYTES 32u

static const uint8_t KEY[16] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f};
static const uint8_t NONCE[16] = {
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f};

/* Associated data: authenticated but NOT encrypted (e.g. a packet header). */
static const uint8_t AD[8] = {'h', 'e', 'a', 'd', 'e', 'r', '0', '1'};

static const char MESSAGE[] = "Politecnico di Milano";

static char nib(uint8_t n) { return (char)((n < 10u) ? (uint32_t)('0' + n) : (uint32_t)('a' + (n - 10u))); }

static void print_hex(const char *label, const uint8_t *data, uint32_t len) {
  neorv32_uart0_printf("%s", label);
  for (uint32_t i = 0u; i < len; ++i) {
    neorv32_uart0_printf("%c%c", nib((uint8_t)(data[i] >> 4)), nib((uint8_t)(data[i] & 0x0fu)));
  }
  neorv32_uart0_printf("\n");
}

/* Print bytes as text, replacing anything unprintable with '.' so a garbled
   decryption is visibly garbled rather than corrupting the terminal. */
static void print_text(const char *label, const uint8_t *data, uint32_t len) {
  neorv32_uart0_printf("%s\"", label);
  for (uint32_t i = 0u; i < len; ++i) {
    const uint8_t c = data[i];
    neorv32_uart0_printf("%c", (c >= 0x20u && c < 0x7fu) ? (char)c : '.');
  }
  neorv32_uart0_printf("\"\n");
}

static uint64_t rdcycle64(void) {
  uint32_t hi0, lo, hi1;
  do {
    __asm__ volatile("rdcycleh %0" : "=r"(hi0));
    __asm__ volatile("rdcycle  %0" : "=r"(lo));
    __asm__ volatile("rdcycleh %0" : "=r"(hi1));
  } while (hi0 != hi1);
  return ((uint64_t)hi0 << 32) | (uint64_t)lo;
}

int main(void) {
  neorv32_rte_setup();
  neorv32_uart0_setup(UART_BAUD, 0);

  const uint32_t msg_len = (uint32_t)(sizeof(MESSAGE) - 1u); /* drop the NUL */

  uint8_t ct[MAX_BYTES];
  uint8_t pt_back[MAX_BYTES];
  uint8_t sw_ct[MAX_BYTES];
  uint8_t sw_tag[16];
  uint8_t hw_tag[16];

  neorv32_uart0_printf("\n");
  neorv32_uart0_printf("=================================================\n");
  neorv32_uart0_printf(" Ascon-AEAD128 hardware accelerator -- live demo\n");
  neorv32_uart0_printf(" NEORV32 RISC-V SoC @ 27 MHz  /  Tang Nano 20K\n");
  neorv32_uart0_printf("=================================================\n\n");

  /* ---- 1. Identify the hardware ------------------------------------- */
  ascon_accel_t accel;
  ascon_accel_init(&accel, ASCON_ACCEL_BASE_ADDR, ACCEL_TIMEOUT_CYCLES);
  ascon_accel_set_data_plane(&accel, ASCON_ACCEL_DATA_PLANE_MMIO_WORD);
  ascon_accel_reset(&accel);

  const uint32_t abi = ascon_accel_abi_version(&accel);
  const uint32_t caps = ascon_accel_capabilities(&accel);
  neorv32_uart0_printf("[1] Accelerator found at 0x%x\n", (uint32_t)ASCON_ACCEL_BASE_ADDR);
  neorv32_uart0_printf("    ABI          : 0x%x\n", abi);
  neorv32_uart0_printf("    CAPABILITIES : 0x%x", caps);
  neorv32_uart0_printf("   (bit0=AEAD128, bit21=cycle counter)\n\n");

  if (msg_len > MAX_BYTES) {
    neorv32_uart0_printf("message too long for the bounded MMIO backend\n");
    return 1;
  }

  print_text("[2] Plaintext        : ", (const uint8_t *)MESSAGE, msg_len);
  print_hex("    Associated data  : ", AD, (uint32_t)sizeof(AD));
  print_hex("    Key              : ", KEY, 16u);
  print_hex("    Nonce            : ", NONCE, 16u);
  neorv32_uart0_printf("\n");

  /* ---- 2. Hardware encrypt ------------------------------------------ */
  ascon_accel_aead_request_t enc;
  memset(&enc, 0, sizeof(enc));
  enc.key = KEY;
  enc.nonce = NONCE;
  enc.ad = AD;
  enc.ad_len = sizeof(AD);
  enc.input = (const uint8_t *)MESSAGE;
  enc.input_len = msg_len;
  enc.output = ct;

  const uint64_t hw_t0 = rdcycle64();
  const ascon_accel_status_t enc_st = ascon_accel_encrypt(&accel, ASCON_ACCEL_MODE_AEAD128, &enc);
  const uint64_t hw_t1 = rdcycle64();
  memcpy(hw_tag, enc.tag, 16u);

  if (enc_st != ASCON_ACCEL_OK) {
    neorv32_uart0_printf("[3] HW encrypt FAILED status=%d err=0x%x\n",
                         (int)enc_st, ascon_accel_error_code(&accel));
    return 1;
  }

  const uint32_t hw_busy = (uint32_t)ascon_accel_cycle_count(&accel);
  const uint32_t hw_wall = (uint32_t)(hw_t1 - hw_t0);

  neorv32_uart0_printf("[3] Hardware encrypt\n");
  print_hex("    Ciphertext       : ", ct, msg_len);
  print_hex("    Tag              : ", hw_tag, 16u);
  neorv32_uart0_printf("    HW busy cycles   : %u   (accelerator START->DONE)\n", hw_busy);
  neorv32_uart0_printf("    HW wall cycles   : %u   (incl. driver setup + readback)\n\n", hw_wall);

  /* ---- 3. Software reference, same CPU, same clock ------------------- */
  const uint64_t sw_t0 = rdcycle64();
  const int sw_rc = ascon_ref_aead128_encrypt(KEY, NONCE, AD, sizeof(AD),
                                              (const uint8_t *)MESSAGE, msg_len,
                                              sw_ct, sw_tag);
  const uint64_t sw_t1 = rdcycle64();
  const uint32_t sw_cy = (uint32_t)(sw_t1 - sw_t0);

  const bool same_ct = (sw_rc == 0) && (memcmp(sw_ct, ct, msg_len) == 0)
                       && (memcmp(sw_tag, hw_tag, 16u) == 0);

  neorv32_uart0_printf("[4] Software (reference C) on the same CPU\n");
  neorv32_uart0_printf("    SW cycles        : %u\n", sw_cy);
  neorv32_uart0_printf("    Identical result : %s\n", same_ct ? "YES" : "NO");
  if (hw_busy > 0u) {
    const uint32_t sp10 = (sw_cy * 10u) / hw_busy;   /* speed-up x10, integer math */
    neorv32_uart0_printf("    Speed-up (engine): %u.%ux   [SW / HW busy]\n", sp10 / 10u, sp10 % 10u);
  }
  if (hw_wall > 0u) {
    const uint32_t sw10 = (sw_cy * 10u) / hw_wall;
    neorv32_uart0_printf("    Speed-up (wall)  : %u.%ux   [SW / HW incl. data movement]\n\n",
                         sw10 / 10u, sw10 % 10u);
  }

  /* ---- 4. Hardware decrypt ------------------------------------------- */
  ascon_accel_aead_request_t dec;
  memset(&dec, 0, sizeof(dec));
  dec.key = KEY;
  dec.nonce = NONCE;
  dec.ad = AD;
  dec.ad_len = sizeof(AD);
  dec.input = ct;
  dec.input_len = msg_len;
  dec.output = pt_back;
  memcpy(dec.tag, hw_tag, 16u);

  const ascon_accel_status_t dec_st = ascon_accel_decrypt(&accel, ASCON_ACCEL_MODE_AEAD128, &dec);
  const bool tag_ok = ascon_accel_tag_valid(&accel);

  neorv32_uart0_printf("[5] Hardware decrypt\n");
  print_text("    Recovered        : ", pt_back, msg_len);
  neorv32_uart0_printf("    Tag valid        : %s\n", (dec_st == ASCON_ACCEL_OK && tag_ok) ? "YES" : "NO");
  neorv32_uart0_printf("    Round-trip       : %s\n\n",
                       (memcmp(pt_back, MESSAGE, msg_len) == 0) ? "MESSAGE RECOVERED" : "MISMATCH");

  /* ---- 5. Tamper test: this is what the tag is for -------------------- */
  neorv32_uart0_printf("[6] Tamper test -- flipping ONE bit of the ciphertext\n");
  uint8_t bad_ct[MAX_BYTES];
  memcpy(bad_ct, ct, msg_len);
  bad_ct[0] ^= 0x01u;      /* single-bit corruption */
  print_hex("    Tampered ct      : ", bad_ct, msg_len);

  ascon_accel_aead_request_t bad;
  memset(&bad, 0, sizeof(bad));
  bad.key = KEY;
  bad.nonce = NONCE;
  bad.ad = AD;
  bad.ad_len = sizeof(AD);
  bad.input = bad_ct;
  bad.input_len = msg_len;
  bad.output = pt_back;
  memcpy(bad.tag, hw_tag, 16u);

  const ascon_accel_status_t bad_st = ascon_accel_decrypt(&accel, ASCON_ACCEL_MODE_AEAD128, &bad);
  const bool bad_tag_ok = ascon_accel_tag_valid(&accel);

  neorv32_uart0_printf("    Tag valid        : %s", (bad_st == ASCON_ACCEL_OK && bad_tag_ok) ? "YES" : "NO");
  neorv32_uart0_printf("    <-- tampering detected by the hardware\n");
  neorv32_uart0_printf("    Driver status    : %d",
                       (int)bad_st);
  neorv32_uart0_printf("   (%s)\n\n", (bad_st == ASCON_ACCEL_ERR_TAG_INVALID) ? "ERR_TAG_INVALID" : "see ascon_accel.h");

  neorv32_uart0_printf("=================================================\n");
  neorv32_uart0_printf(" Demo complete.\n");
  neorv32_uart0_printf("=================================================\n");

  while (1) {
    /* idle */
  }
  return 0;
}
