#include <stdint.h>
#include <string.h>

#include <neorv32.h>

#include "../ascon_accel/ascon_accel.h"

#define UART_BAUD 19200u
#define ACCEL_TIMEOUT_CYCLES 10000000u

static void print_hex(const char *label, const uint8_t *data, uint32_t len) {
  neorv32_uart0_printf("%s", label);
  for (uint32_t i = 0; i < len; ++i) {
    neorv32_uart0_printf("%02x", data[i]);
  }
  neorv32_uart0_printf("\n");
}

int main(void) {
  neorv32_rte_setup();
  neorv32_uart0_setup(UART_BAUD, 0);

  neorv32_uart0_printf("pyrilascon NEORV32 accelerator demo\n");

  ascon_accel_t accel;
  ascon_accel_init(&accel, ASCON_ACCEL_BASE_ADDR, ACCEL_TIMEOUT_CYCLES);
  ascon_accel_reset(&accel);

  const uint32_t abi = ascon_accel_abi_version(&accel);
  const uint32_t caps = ascon_accel_capabilities(&accel);
  neorv32_uart0_printf("ABI  : 0x%x\n", abi);
  neorv32_uart0_printf("CAPS : 0x%x\n", caps);

  if (abi != ASCON_ACCEL_ABI_VERSION) {
    neorv32_uart0_printf("ERROR: ABI mismatch\n");
    return 1;
  }
  if (!ascon_accel_supports(&accel, ASCON_ACCEL_MODE_AEAD128)) {
    neorv32_uart0_printf("ERROR: AEAD128 not supported by this hardware\n");
    return 1;
  }

  const uint8_t key[16] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
  };
  const uint8_t nonce[16] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
  };
  const uint8_t ad[8] = {
    0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
  };
  const uint8_t plaintext[16] = {
    0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
    0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff,
  };

  uint8_t ciphertext[sizeof(plaintext)] = {0};
  uint8_t tag[16] = {0};

  ascon_accel_aead_request_t req;
  memset(&req, 0, sizeof(req));
  req.key = key;
  req.nonce = nonce;
  req.ad = ad;
  req.ad_len = sizeof(ad);
  req.input = plaintext;
  req.input_len = sizeof(plaintext);
  req.output = ciphertext;
  memcpy(req.tag, tag, sizeof(tag));

  const ascon_accel_status_t status = ascon_accel_encrypt(&accel, ASCON_ACCEL_MODE_AEAD128, &req);
  if (status != ASCON_ACCEL_OK) {
    neorv32_uart0_printf("ERROR: encrypt failed: %d, hw error 0x%x\n", (int)status, ascon_accel_error_code(&accel));
    return 1;
  }

  print_hex("CT   : ", ciphertext, sizeof(ciphertext));
  print_hex("TAG  : ", req.tag, sizeof(req.tag));
  neorv32_uart0_printf("CYC  : %u\n", (uint32_t)ascon_accel_cycle_count(&accel));
  neorv32_uart0_printf("DONE\n");
  return 0;
}
