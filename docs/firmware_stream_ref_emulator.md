# Firmware AXI Stream reference emulator

`firmware/ascon_accel/ascon_accel_axis_ref_emulator.c` is a host-side test
fixture for the stream-native firmware path. It is not synthesizable RTL and is
not intended to run on NEORV32.

The emulator connects to the normal firmware driver through
`ascon_accel_axis_transport_t`:

```text
ascon_accel_encrypt/decrypt
  -> MMIO register image
  -> AXI Stream send/recv callbacks
  -> portable C Ascon-AEAD128 reference implementation
```

It reads the same register image as the real accelerator:

- `MODE`
- `CONTROL.START`
- `CONTROL.DECRYPT`
- `KEY0..KEY3`
- `NONCE0..NONCE3`
- `AD_LEN`
- `TEXT_LEN`
- `TAG0..TAG3` for decrypt tag input

For encryption it captures AD and plaintext streams, computes ciphertext/tag
with `ascon_ref_aead128_encrypt`, places ciphertext in the transport receive
queue, writes `TAG0..TAG3`, and reports `DONE | TAG_VALID`.

For decrypt it captures AD and ciphertext streams, computes plaintext and tag
validation with `ascon_ref_aead128_decrypt`, and only exposes plaintext through
`recv` if authentication succeeds. If authentication fails it reports
`ASCON_ERROR_TAG_INVALID` and leaves the receive queue empty, matching the
buffered decrypt security policy.

This gives the project an end-to-end firmware test that validates the software
ABI and AXI-stream sequencing before moving to NEORV32, DMA, or board demos.
