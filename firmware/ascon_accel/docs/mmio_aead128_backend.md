# AEAD128 MMIO Backend

`rtl/common/ascon_aead128_mmio_backend.v` is the first real cryptographic
backend connected to the frozen accelerator register map.

It currently supports a deliberately bounded profile:

- NIST Ascon-AEAD128 only;
- one Ascon round per clock cycle;
- up to 32 bytes of associated data;
- up to 32 bytes of plaintext/ciphertext;
- software pushes input as 32-bit `DATA_IN` beats with `DATA_IN_CTRL`;
- software reads output as 32-bit `DATA_OUT` beats;
- decrypt output is zeroized and not exposed when the tag check fails.

This backend is intended for early NEORV32 integration and ABI validation.  It is
not the final high-throughput FPGA architecture.

The Tang Nano 9K target `boards/tangnano9k/ascon_aead128_mmio_slow` instantiates
this backend and runs an encryption/decryption KAT through the register map.
