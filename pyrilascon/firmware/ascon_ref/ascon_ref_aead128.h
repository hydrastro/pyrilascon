#ifndef ASCON_REF_AEAD128_H
#define ASCON_REF_AEAD128_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ASCON_REF_AEAD128_KEY_BYTES 16u
#define ASCON_REF_AEAD128_NONCE_BYTES 16u
#define ASCON_REF_AEAD128_TAG_BYTES 16u

int ascon_ref_aead128_encrypt(
    const uint8_t key[ASCON_REF_AEAD128_KEY_BYTES],
    const uint8_t nonce[ASCON_REF_AEAD128_NONCE_BYTES],
    const uint8_t *associated_data,
    size_t associated_data_len,
    const uint8_t *plaintext,
    size_t plaintext_len,
    uint8_t *ciphertext,
    uint8_t tag[ASCON_REF_AEAD128_TAG_BYTES]);

int ascon_ref_aead128_decrypt(
    const uint8_t key[ASCON_REF_AEAD128_KEY_BYTES],
    const uint8_t nonce[ASCON_REF_AEAD128_NONCE_BYTES],
    const uint8_t *associated_data,
    size_t associated_data_len,
    const uint8_t *ciphertext,
    size_t ciphertext_len,
    const uint8_t tag[ASCON_REF_AEAD128_TAG_BYTES],
    uint8_t *plaintext,
    bool *valid);

#ifdef __cplusplus
}
#endif

#endif
