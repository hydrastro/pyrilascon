# Unified streaming AEAD128 backend

`rtl/stream/ascon_aead128_stream.v` is the SoC-facing AXI Stream AEAD128 backend.
It preserves the frozen control-plane contract while hiding the internal split
between encryption and authenticated decryption implementations.

## Dispatch policy

The wrapper samples `decrypt_i` when `start_i` is asserted:

- `decrypt_i = 0` selects `ascon_aead128_stream_encrypt`.
- `decrypt_i = 1` selects `ascon_aead128_stream_decrypt_buffered`.

The selected operation owns `s_axis_tready`, all output-stream signals, and all
status outputs until the next `clear_i` or `start_i`.

## Encryption path

Encryption remains unbounded and stream-native.  AD is received first, plaintext
is received second, ciphertext is emitted as plaintext beats are processed, and
`generated_tag_o` is valid when the operation completes.

## Decryption path

Decryption remains conservative and authenticated.  Ciphertext is decrypted into
the internal quarantine buffer in `ascon_aead128_stream_decrypt_buffered`.
Plaintext is released on `m_axis` only after `generated_tag_o == expected_tag_i`.
If the tag is invalid, no plaintext beat is emitted and
`ASCON_ERROR_TAG_INVALID` is reported.

## Why this wrapper exists

The firmware, NEORV32 CFS wrapper, DMA frontend, and future board demos should
not bind directly to separate encrypt/decrypt RTL modules.  They should bind to
this unified backend and select operation direction with the same ABI `decrypt`
bit already used by the firmware control layer.

The split implementation is intentionally kept below this wrapper because the
architectural policies differ:

- encryption can be fully streaming and unbounded;
- safe decrypt requires bounded internal storage or an external quarantine/DMA
  region before plaintext can be committed.
