#include "ascon_accel.h"

static const uint8_t key[16] = {
  0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
  0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
};

static const uint8_t nonce[16] = {
  0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
  0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
};

static const uint8_t ad[] = { 'A', 'D', '1', '2', '3' };
static const uint8_t plaintext[] = "hello ASCON hardware model";

int main(void) {
  ascon_accel_t ascon;
  ascon_accel_init(&ascon, ASCON_ACCEL_BASE_ADDR, 1000000u);

  uint8_t ciphertext[sizeof(plaintext) - 1u];
  ascon_accel_aead_request_t req = {
    .key = key,
    .nonce = nonce,
    .ad = ad,
    .ad_len = sizeof(ad),
    .input = plaintext,
    .input_len = sizeof(plaintext) - 1u,
    .output = ciphertext,
    .tag = {0},
  };

  ascon_accel_status_t status = ascon_accel_encrypt(&ascon, ASCON_ACCEL_MODE_AEAD128, &req);
  if (status != ASCON_ACCEL_OK) {
    return 1;
  }

  uint8_t decrypted[sizeof(plaintext) - 1u];
  ascon_accel_aead_request_t dec_req = req;
  dec_req.input = ciphertext;
  dec_req.output = decrypted;

  status = ascon_accel_decrypt(&ascon, ASCON_ACCEL_MODE_AEAD128, &dec_req);
  if (status != ASCON_ACCEL_OK) {
    return 2;
  }

  for (unsigned i = 0; i < sizeof(decrypted); ++i) {
    if (decrypted[i] != plaintext[i]) {
      return 3;
    }
  }
  return 0;
}
