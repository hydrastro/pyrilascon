# Streaming AEAD128 SoC Top

`rtl/common/ascon_accel_stream_aead128_top.v` is the first firmware-facing top
level for the real stream-native AEAD128 backend.

It keeps the frozen MMIO register ABI and exposes a 128-bit AXI4-Stream-style
bulk data plane:

- MMIO configures `CONTROL`, `MODE`, lengths, key, nonce, expected tag, status,
  cycle count, and error code.
- `s_axis` carries associated data first, then plaintext for encryption or
  ciphertext for decryption.
- `m_axis` emits ciphertext for encryption or authenticated plaintext for
  decryption.
- `CONTROL.DECRYPT = 0` selects streaming encrypt.
- `CONTROL.DECRYPT = 1` selects buffered authenticated decrypt.

The wrapper instantiates:

```text
ascon_accel_mmio_regs
    +
ascon_aead128_stream
```

The top advertises these relevant capabilities through `ASCON_REG_CAPABILITIES`:

```text
ASCON_CAP_AEAD128
ASCON_CAP_DECRYPT_BUFFERED
ASCON_CAP_CONSTTIME_TAG_COMPARE
ASCON_CAP_STREAMING_BYTEMASK
ASCON_CAP_CYCLE_COUNTER
ASCON_CAP_AXI_STREAM_DATA
```

## Data-plane boundary

This top is stream-native. The legacy MMIO `DATA_IN` and `DATA_OUT` registers are
retained only to keep the ABI shape and expose low-word output/status for debug.
Bulk payload transfer must use AXI Stream.

The older `ascon_accel_axis_aead128_top` remains as a bounded compatibility
wrapper around the MMIO backend. New SoC, DMA, and NEORV32 integration work should
target `ascon_accel_stream_aead128_top`.

## Decrypt policy

Decryption inherits the conservative policy from
`ascon_aead128_stream_decrypt_buffered`: plaintext is quarantined internally and
is released only if the computed tag matches the expected tag programmed through
the TAG registers.

If authentication fails, the top reports `ASCON_ERROR_TAG_INVALID` and no
plaintext is released on `m_axis`.
