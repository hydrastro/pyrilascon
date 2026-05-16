from ascon_hwmodel import AEADVariant, aead_decrypt, aead_encrypt, ascon_hash256, ascon_xof128, ascon_cxof128

key = bytes(range(16))
nonce = bytes(range(16, 32))
ad = b"associated-data"
plaintext = b"hello ASCON hardware model"

enc = aead_encrypt(key, nonce, ad, plaintext, AEADVariant.NIST_AEAD128)
print("ciphertext:", enc.ciphertext.hex())
print("tag:       ", enc.tag.hex())

dec = aead_decrypt(key, nonce, ad, enc.ciphertext, enc.tag, AEADVariant.NIST_AEAD128)
print("valid:     ", dec.valid)
print("plaintext: ", dec.plaintext)

print("hash256:   ", ascon_hash256(b"abc").hex())
print("xof16:     ", ascon_xof128(b"abc", 16).hex())
print("cxof16:    ", ascon_cxof128(b"abc", 16, b"demo").hex())
