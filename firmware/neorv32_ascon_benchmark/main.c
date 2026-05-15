#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include <neorv32.h>

#include "../ascon_accel/ascon_accel.h"
#include "../ascon_accel/ascon_accel_benchmark.h"
#include "../ascon_ref/ascon_ref_aead128.h"

#define UART_BAUD 19200u
#define ACCEL_TIMEOUT_CYCLES 10000000u
#define BENCH_TEXT_BYTES 32u
#define BENCH_AD_BYTES 16u

static uint64_t rdcycle64(void) {
#if __riscv_xlen == 64
  uint64_t value;
  __asm__ volatile ("rdcycle %0" : "=r"(value));
  return value;
#else
  uint32_t hi0;
  uint32_t lo;
  uint32_t hi1;
  do {
    __asm__ volatile ("rdcycleh %0" : "=r"(hi0));
    __asm__ volatile ("rdcycle %0" : "=r"(lo));
    __asm__ volatile ("rdcycleh %0" : "=r"(hi1));
  } while (hi0 != hi1);
  return ((uint64_t)hi1 << 32) | (uint64_t)lo;
#endif
}

static void print_hex(const char *label, const uint8_t *data, uint32_t len) {
  neorv32_uart0_printf("%s", label);
  for (uint32_t i = 0u; i < len; ++i) {
    neorv32_uart0_printf("%02x", data[i]);
  }
  neorv32_uart0_printf("\n");
}

static bool bytes_equal(const uint8_t *a, const uint8_t *b, uint32_t len) {
  uint8_t diff = 0u;
  for (uint32_t i = 0u; i < len; ++i) {
    diff |= (uint8_t)(a[i] ^ b[i]);
  }
  return diff == 0u;
}

static void print_benchmark_result(
    const char *label,
    const ascon_accel_benchmark_result_t *result) {
  neorv32_uart0_printf("%s status       : %d\n", label, (int)result->status);
  neorv32_uart0_printf("%s hw cycles    : %u:%u\n", label,
                       (uint32_t)(result->elapsed_cycles >> 32),
                       (uint32_t)(result->elapsed_cycles & 0xffffffffu));
  neorv32_uart0_printf("%s hw mcy/byte  : %u\n", label,
                       (uint32_t)ascon_accel_benchmark_mcycles_per_byte(result));
  neorv32_uart0_printf("%s tag valid    : %u\n", label, result->tag_valid ? 1u : 0u);
  neorv32_uart0_printf("%s hw err       : 0x%x\n", label, result->error_code);
}

int main(void) {
  neorv32_rte_setup();
  neorv32_uart0_setup(UART_BAUD, 0);

  neorv32_uart0_printf("pyrilascon NEORV32 ASCON benchmark\n");

  const uint8_t key[16] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
  };
  const uint8_t nonce[16] = {
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
  };
  const uint8_t ad[BENCH_AD_BYTES] = {
    0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
    0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f,
  };
  const uint8_t plaintext[BENCH_TEXT_BYTES] = {
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
    0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
    0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47,
    0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f,
  };

  uint8_t sw_ciphertext[BENCH_TEXT_BYTES] = {0};
  uint8_t sw_tag[16] = {0};
  uint8_t sw_decrypted[BENCH_TEXT_BYTES] = {0};
  bool sw_valid = false;

  const uint64_t sw_start = rdcycle64();
  const int sw_enc_status = ascon_ref_aead128_encrypt(
      key, nonce, ad, sizeof(ad), plaintext, sizeof(plaintext), sw_ciphertext, sw_tag);
  const int sw_dec_status = ascon_ref_aead128_decrypt(
      key, nonce, ad, sizeof(ad), sw_ciphertext, sizeof(sw_ciphertext), sw_tag, sw_decrypted, &sw_valid);
  const uint64_t sw_end = rdcycle64();
  const uint64_t sw_cycles = sw_end - sw_start;

  if (sw_enc_status != 0 || sw_dec_status != 0 || !sw_valid ||
      !bytes_equal(sw_decrypted, plaintext, sizeof(plaintext))) {
    neorv32_uart0_printf("ERROR: software reference failed\n");
    return 1;
  }

  ascon_accel_t accel;
  ascon_accel_init(&accel, ASCON_ACCEL_BASE_ADDR, ACCEL_TIMEOUT_CYCLES);
  ascon_accel_reset(&accel);

  const uint32_t abi = ascon_accel_abi_version(&accel);
  const uint32_t caps = ascon_accel_capabilities(&accel);
  neorv32_uart0_printf("ABI          : 0x%x\n", abi);
  neorv32_uart0_printf("CAPS         : 0x%x\n", caps);

  if (abi != ASCON_ACCEL_ABI_VERSION) {
    neorv32_uart0_printf("ERROR: ABI mismatch\n");
    return 1;
  }
  if (!ascon_accel_supports(&accel, ASCON_ACCEL_MODE_AEAD128)) {
    neorv32_uart0_printf("ERROR: AEAD128 not supported\n");
    return 1;
  }

  uint8_t hw_ciphertext[BENCH_TEXT_BYTES] = {0};
  uint8_t hw_tag[16] = {0};
  ascon_accel_aead_request_t enc_req;
  memset(&enc_req, 0, sizeof(enc_req));
  enc_req.key = key;
  enc_req.nonce = nonce;
  enc_req.ad = ad;
  enc_req.ad_len = sizeof(ad);
  enc_req.input = plaintext;
  enc_req.input_len = sizeof(plaintext);
  enc_req.output = hw_ciphertext;
  memcpy(enc_req.tag, hw_tag, sizeof(hw_tag));

  ascon_accel_benchmark_result_t hw_enc_result;
  const ascon_accel_status_t hw_enc_status = ascon_accel_benchmark_encrypt(
      &accel, ASCON_ACCEL_MODE_AEAD128, &enc_req, &hw_enc_result);
  memcpy(hw_tag, enc_req.tag, sizeof(hw_tag));

  uint8_t hw_decrypted[BENCH_TEXT_BYTES] = {0};
  ascon_accel_aead_request_t dec_req;
  memset(&dec_req, 0, sizeof(dec_req));
  dec_req.key = key;
  dec_req.nonce = nonce;
  dec_req.ad = ad;
  dec_req.ad_len = sizeof(ad);
  dec_req.input = hw_ciphertext;
  dec_req.input_len = sizeof(hw_ciphertext);
  dec_req.output = hw_decrypted;
  memcpy(dec_req.tag, hw_tag, sizeof(hw_tag));

  ascon_accel_benchmark_result_t hw_dec_result;
  const ascon_accel_status_t hw_dec_status = ascon_accel_benchmark_decrypt(
      &accel, ASCON_ACCEL_MODE_AEAD128, &dec_req, &hw_dec_result);

  print_hex("SW CT        : ", sw_ciphertext, sizeof(sw_ciphertext));
  print_hex("SW TAG       : ", sw_tag, sizeof(sw_tag));
  print_hex("HW CT        : ", hw_ciphertext, sizeof(hw_ciphertext));
  print_hex("HW TAG       : ", hw_tag, sizeof(hw_tag));
  print_hex("HW PT        : ", hw_decrypted, sizeof(hw_decrypted));

  print_benchmark_result("ENC", &hw_enc_result);
  print_benchmark_result("DEC", &hw_dec_result);

  const bool enc_ok = hw_enc_status == ASCON_ACCEL_OK &&
                      bytes_equal(hw_ciphertext, sw_ciphertext, sizeof(sw_ciphertext)) &&
                      bytes_equal(hw_tag, sw_tag, sizeof(sw_tag));
  const bool dec_ok = hw_dec_status == ASCON_ACCEL_OK &&
                      bytes_equal(hw_decrypted, plaintext, sizeof(plaintext));

  neorv32_uart0_printf("SW cycles    : %u:%u\n",
                       (uint32_t)(sw_cycles >> 32),
                       (uint32_t)(sw_cycles & 0xffffffffu));

  if (hw_enc_result.elapsed_cycles != 0u) {
    const uint32_t speedup_x1000 = (uint32_t)((sw_cycles * 1000u) / hw_enc_result.elapsed_cycles);
    neorv32_uart0_printf("ENC speedup x1000: %u\n", speedup_x1000);
  }
  if (hw_dec_result.elapsed_cycles != 0u) {
    const uint32_t speedup_x1000 = (uint32_t)((sw_cycles * 1000u) / hw_dec_result.elapsed_cycles);
    neorv32_uart0_printf("DEC speedup x1000: %u\n", speedup_x1000);
  }

  if (!enc_ok) {
    neorv32_uart0_printf("FAIL: encryption mismatch\n");
    return 1;
  }
  if (!dec_ok) {
    neorv32_uart0_printf("FAIL: decryption mismatch\n");
    return 1;
  }
  if (hw_enc_result.elapsed_cycles >= sw_cycles) {
    neorv32_uart0_printf("WARN: hardware encryption did not beat software for this shape\n");
  }
  if (hw_dec_result.elapsed_cycles >= sw_cycles) {
    neorv32_uart0_printf("WARN: hardware decryption did not beat software for this shape\n");
  }

  neorv32_uart0_printf("PASS\n");
  return 0;
}
