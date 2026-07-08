/*
 * Host-native self-test for the ascon_accel driver (the "interact via C" path).
 *
 * Drives the real driver through the AXI-stream ref-emulator transport, which
 * models the accelerator by computing Ascon-AEAD128 in software and updating
 * the same MMIO register image the driver reads. No hardware is required.
 *
 * The produced ciphertext/tag are checked against the standalone portable C
 * reference *in the same binary* (which tests/test_reference_c.py already pins
 * bit-exact to the NIST-verified model), and a full encrypt->decrypt round trip
 * is verified. Prints a single PASS/FAIL line.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ascon_accel.h"
#include "ascon_accel_axis_ref_emulator.h"
#include "ascon_ref_aead128.h"

static int diff(const char *what, const uint8_t *a, const uint8_t *b, size_t n) {
  if (memcmp(a, b, n) != 0) {
    printf("MISMATCH %s\n", what);
    return 1;
  }
  return 0;
}

int main(void) {
  static volatile uint32_t regs[256];
  memset((void *)regs, 0, sizeof(regs));

  ascon_accel_t dev;
  ascon_accel_init(&dev, (uintptr_t)regs, 1000000u);
  ascon_accel_set_data_plane(&dev, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL);

  ascon_accel_axis_ref_emulator_ctx_t emu;
  ascon_accel_axis_ref_emulator_init(&emu, regs);
  ascon_accel_axis_transport_t transport = ascon_accel_axis_ref_emulator_transport(&emu);
  ascon_accel_set_axis_transport(&dev, &transport);

  uint8_t key[16], nonce[16], ad[16], pt[32];
  for (unsigned i = 0; i < 16u; ++i) {
    key[i] = (uint8_t)i;
    nonce[i] = (uint8_t)(0x10u + i);
    ad[i] = (uint8_t)(0x20u + i);
  }
  for (unsigned i = 0; i < 32u; ++i) {
    pt[i] = (uint8_t)(0x30u + i);
  }

  /* Driver encrypt through the emulated accelerator. */
  uint8_t hw_ct[32];
  ascon_accel_aead_request_t enc;
  memset(&enc, 0, sizeof(enc));
  enc.key = key;
  enc.nonce = nonce;
  enc.ad = ad;
  enc.ad_len = sizeof(ad);
  enc.input = pt;
  enc.input_len = sizeof(pt);
  enc.output = hw_ct;
  if (ascon_accel_encrypt(&dev, ASCON_ACCEL_MODE_AEAD128, &enc) != ASCON_ACCEL_OK) {
    printf("FAIL driver encrypt status=%d\n", ascon_accel_error_code(&dev));
    return 1;
  }

  /* Reference encrypt in the same binary. */
  uint8_t ref_ct[32], ref_tag[16];
  ascon_ref_aead128_encrypt(key, nonce, ad, sizeof(ad), pt, sizeof(pt), ref_ct, ref_tag);

  int errors = 0;
  errors += diff("ciphertext (driver vs reference)", hw_ct, ref_ct, sizeof(hw_ct));
  errors += diff("tag (driver vs reference)", enc.tag, ref_tag, 16);

  /* Full round trip: driver decrypt must recover the plaintext and accept the tag. */
  uint8_t hw_pt[32];
  ascon_accel_aead_request_t dec;
  memset(&dec, 0, sizeof(dec));
  dec.key = key;
  dec.nonce = nonce;
  dec.ad = ad;
  dec.ad_len = sizeof(ad);
  dec.input = hw_ct;
  dec.input_len = sizeof(hw_ct);
  dec.output = hw_pt;
  memcpy(dec.tag, enc.tag, 16);
  if (ascon_accel_decrypt(&dev, ASCON_ACCEL_MODE_AEAD128, &dec) != ASCON_ACCEL_OK) {
    printf("FAIL driver decrypt status=%d\n", ascon_accel_error_code(&dev));
    return 1;
  }
  if (!ascon_accel_tag_valid(&dev)) {
    printf("FAIL tag not accepted on round trip\n");
    errors += 1;
  }
  errors += diff("round-trip plaintext", hw_pt, pt, sizeof(hw_pt));

  if (errors == 0) {
    printf("PASS driver+emulator match reference (ct+tag) and round-trip ok\n");
    return 0;
  }
  printf("FAIL %d mismatch(es)\n", errors);
  return 1;
}
