#include "ascon_ref_aead128.h"

#include <string.h>

#define ASCON_AEAD128_RATE_BYTES 16u
#define ASCON_AEAD128_IV UINT64_C(0x00001000808C0001)
#define ASCON_MASK64 UINT64_C(0xFFFFFFFFFFFFFFFF)

typedef struct {
  uint64_t x0;
  uint64_t x1;
  uint64_t x2;
  uint64_t x3;
  uint64_t x4;
} ascon_state_t;

static uint64_t load64_le(const uint8_t *src) {
  uint64_t value = 0u;
  for (unsigned i = 0u; i < 8u; ++i) {
    value |= ((uint64_t)src[i]) << (8u * i);
  }
  return value;
}

static void store64_le(uint8_t *dst, uint64_t value) {
  for (unsigned i = 0u; i < 8u; ++i) {
    dst[i] = (uint8_t)((value >> (8u * i)) & 0xffu);
  }
}

static uint64_t rotr64(uint64_t value, unsigned amount) {
  return (value >> amount) | (value << (64u - amount));
}

static uint8_t round_constant(unsigned rounds, unsigned round_index) {
  static const uint8_t constants[16] = {
      0x3c, 0x2d, 0x1e, 0x0f,
      0xf0, 0xe1, 0xd2, 0xc3,
      0xb4, 0xa5, 0x96, 0x87,
      0x78, 0x69, 0x5a, 0x4b,
  };
  return constants[16u - rounds + round_index];
}

static void p_c(ascon_state_t *s, unsigned rounds, unsigned round_index) {
  s->x2 ^= (uint64_t)round_constant(rounds, round_index);
}

static void p_s(ascon_state_t *s) {
  const uint64_t x0 = s->x0;
  const uint64_t x1 = s->x1;
  const uint64_t x2 = s->x2;
  const uint64_t x3 = s->x3;
  const uint64_t x4 = s->x4;

  const uint64_t y0 = ((x4 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ (x1 & x0) ^ x1 ^ x0) & ASCON_MASK64;
  const uint64_t y1 = (x4 ^ (x3 & x2) ^ (x3 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ x1 ^ x0) & ASCON_MASK64;
  const uint64_t y2 = ((x4 & x3) ^ x4 ^ x2 ^ x1 ^ ASCON_MASK64) & ASCON_MASK64;
  const uint64_t y3 = ((x4 & x0) ^ x4 ^ (x3 & x0) ^ x3 ^ x2 ^ x1 ^ x0) & ASCON_MASK64;
  const uint64_t y4 = ((x4 & x1) ^ x4 ^ x3 ^ (x1 & x0) ^ x1) & ASCON_MASK64;

  s->x0 = y0;
  s->x1 = y1;
  s->x2 = y2;
  s->x3 = y3;
  s->x4 = y4;
}

static void p_l(ascon_state_t *s) {
  s->x0 ^= rotr64(s->x0, 19u) ^ rotr64(s->x0, 28u);
  s->x1 ^= rotr64(s->x1, 61u) ^ rotr64(s->x1, 39u);
  s->x2 ^= rotr64(s->x2, 1u) ^ rotr64(s->x2, 6u);
  s->x3 ^= rotr64(s->x3, 10u) ^ rotr64(s->x3, 17u);
  s->x4 ^= rotr64(s->x4, 7u) ^ rotr64(s->x4, 41u);
}

static void ascon_permute(ascon_state_t *s, unsigned rounds) {
  for (unsigned round_index = 0u; round_index < rounds; ++round_index) {
    p_c(s, rounds, round_index);
    p_s(s);
    p_l(s);
  }
}

static void rate_to_bytes(const ascon_state_t *s, uint8_t out[ASCON_AEAD128_RATE_BYTES]) {
  store64_le(out, s->x0);
  store64_le(out + 8u, s->x1);
}

static void bytes_to_rate(ascon_state_t *s, const uint8_t in[ASCON_AEAD128_RATE_BYTES]) {
  s->x0 = load64_le(in);
  s->x1 = load64_le(in + 8u);
}

static void xor_rate_block(ascon_state_t *s, const uint8_t block[ASCON_AEAD128_RATE_BYTES]) {
  s->x0 ^= load64_le(block);
  s->x1 ^= load64_le(block + 8u);
}

static void make_padded_block(
    uint8_t block[ASCON_AEAD128_RATE_BYTES],
    const uint8_t *data,
    size_t len) {
  memset(block, 0, ASCON_AEAD128_RATE_BYTES);
  if (len > 0u && data != 0) {
    memcpy(block, data, len);
  }
  block[len] ^= 0x01u;
}

static int validate_common(
    const uint8_t *key,
    const uint8_t *nonce,
    const uint8_t *ad,
    size_t ad_len,
    const uint8_t *input,
    size_t input_len,
    const uint8_t *output) {
  if (key == 0 || nonce == 0 || output == 0) {
    return -1;
  }
  if (ad_len > 0u && ad == 0) {
    return -1;
  }
  if (input_len > 0u && input == 0) {
    return -1;
  }
  return 0;
}

static void initialize(ascon_state_t *s, const uint8_t key[16], const uint8_t nonce[16]) {
  const uint64_t k0 = load64_le(key);
  const uint64_t k1 = load64_le(key + 8u);
  s->x0 = ASCON_AEAD128_IV;
  s->x1 = k0;
  s->x2 = k1;
  s->x3 = load64_le(nonce);
  s->x4 = load64_le(nonce + 8u);
  ascon_permute(s, 12u);
  s->x3 ^= k0;
  s->x4 ^= k1;
}

static void process_ad(ascon_state_t *s, const uint8_t *ad, size_t ad_len) {
  uint8_t block[ASCON_AEAD128_RATE_BYTES];
  size_t offset = 0u;
  if (ad_len > 0u) {
    while ((ad_len - offset) >= ASCON_AEAD128_RATE_BYTES) {
      xor_rate_block(s, ad + offset);
      ascon_permute(s, 8u);
      offset += ASCON_AEAD128_RATE_BYTES;
    }
    make_padded_block(block, ad + offset, ad_len - offset);
    xor_rate_block(s, block);
    ascon_permute(s, 8u);
  }
  s->x4 ^= UINT64_C(0x8000000000000000);
}

static void finalize_tag(ascon_state_t *s, const uint8_t key[16], uint8_t tag[16]) {
  const uint64_t k0 = load64_le(key);
  const uint64_t k1 = load64_le(key + 8u);
  s->x2 ^= k0;
  s->x3 ^= k1;
  ascon_permute(s, 12u);
  store64_le(tag, s->x3 ^ k0);
  store64_le(tag + 8u, s->x4 ^ k1);
}

static bool consttime_equal16(const uint8_t left[16], const uint8_t right[16]) {
  uint8_t diff = 0u;
  for (unsigned i = 0u; i < 16u; ++i) {
    diff |= (uint8_t)(left[i] ^ right[i]);
  }
  return diff == 0u;
}

int ascon_ref_aead128_encrypt(
    const uint8_t key[16],
    const uint8_t nonce[16],
    const uint8_t *associated_data,
    size_t associated_data_len,
    const uint8_t *plaintext,
    size_t plaintext_len,
    uint8_t *ciphertext,
    uint8_t tag[16]) {
  if (validate_common(key, nonce, associated_data, associated_data_len, plaintext, plaintext_len, ciphertext) != 0 || tag == 0) {
    return -1;
  }

  ascon_state_t s;
  initialize(&s, key, nonce);
  process_ad(&s, associated_data, associated_data_len);

  uint8_t rate[ASCON_AEAD128_RATE_BYTES];
  uint8_t final_block[ASCON_AEAD128_RATE_BYTES];
  size_t offset = 0u;
  while ((plaintext_len - offset) >= ASCON_AEAD128_RATE_BYTES) {
    xor_rate_block(&s, plaintext + offset);
    rate_to_bytes(&s, rate);
    memcpy(ciphertext + offset, rate, ASCON_AEAD128_RATE_BYTES);
    ascon_permute(&s, 8u);
    offset += ASCON_AEAD128_RATE_BYTES;
  }

  const size_t final_len = plaintext_len - offset;
  make_padded_block(final_block, plaintext + offset, final_len);
  xor_rate_block(&s, final_block);
  rate_to_bytes(&s, rate);
  if (final_len > 0u) {
    memcpy(ciphertext + offset, rate, final_len);
  }

  finalize_tag(&s, key, tag);
  return 0;
}

int ascon_ref_aead128_decrypt(
    const uint8_t key[16],
    const uint8_t nonce[16],
    const uint8_t *associated_data,
    size_t associated_data_len,
    const uint8_t *ciphertext,
    size_t ciphertext_len,
    const uint8_t tag[16],
    uint8_t *plaintext,
    bool *valid) {
  if (validate_common(key, nonce, associated_data, associated_data_len, ciphertext, ciphertext_len, plaintext) != 0 || tag == 0 || valid == 0) {
    return -1;
  }

  ascon_state_t s;
  initialize(&s, key, nonce);
  process_ad(&s, associated_data, associated_data_len);

  uint8_t rate[ASCON_AEAD128_RATE_BYTES];
  uint8_t new_rate[ASCON_AEAD128_RATE_BYTES];
  size_t offset = 0u;
  while ((ciphertext_len - offset) >= ASCON_AEAD128_RATE_BYTES) {
    rate_to_bytes(&s, rate);
    for (unsigned i = 0u; i < ASCON_AEAD128_RATE_BYTES; ++i) {
      plaintext[offset + i] = (uint8_t)(rate[i] ^ ciphertext[offset + i]);
      new_rate[i] = ciphertext[offset + i];
    }
    bytes_to_rate(&s, new_rate);
    ascon_permute(&s, 8u);
    offset += ASCON_AEAD128_RATE_BYTES;
  }

  const size_t final_len = ciphertext_len - offset;
  rate_to_bytes(&s, rate);
  memcpy(new_rate, rate, ASCON_AEAD128_RATE_BYTES);
  for (size_t i = 0u; i < final_len; ++i) {
    plaintext[offset + i] = (uint8_t)(rate[i] ^ ciphertext[offset + i]);
    new_rate[i] = ciphertext[offset + i];
  }
  new_rate[final_len] ^= 0x01u;
  bytes_to_rate(&s, new_rate);

  uint8_t computed_tag[16];
  finalize_tag(&s, key, computed_tag);
  *valid = consttime_equal16(computed_tag, tag);
  if (!*valid && ciphertext_len > 0u) {
    memset(plaintext, 0, ciphertext_len);
  }
  return 0;
}
