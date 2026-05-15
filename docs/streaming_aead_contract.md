# Streaming AEAD128 Contract

This document freezes the first true AXI4-Stream AEAD128 data-plane contract for
pyrilascon.  The existing MMIO/CSR register map remains the control plane; AXI
Stream carries only payload bytes.

## Control plane stays frozen

The following fields are still configured through the accelerator ABI:

- `CONTROL`, `STATUS`, `MODE`, and `CAPABILITIES`;
- `AD_LEN`, `TEXT_LEN`, `OUT_LEN`, and `CUSTOM_LEN`;
- `KEY0..KEY3` and `NONCE0..NONCE3`;
- expected/generated `TAG0..TAG3`;
- `ERROR_CODE` and `CYCLE_COUNT`.

The stream backend must therefore be replaceable without changing firmware API
calls or the public register map.

## Stream phases

AEAD128 uses two logical input streams:

1. Associated data, identified by `ASCON_AXIS_USER_AD`.
2. Text, identified by `ASCON_AXIS_USER_TEXT`.

For encryption, the text input is plaintext and the text output is ciphertext.
For decryption, the text input is ciphertext and the text output is plaintext.
Tag input/output remains scalar through the frozen tag registers for the first
streaming milestone.

## AXI beat rules

For every AD or text packet:

- `tdata` carries little-endian byte lanes; lane 0 is `tdata[7:0]`.
- `tkeep[i]` marks byte lane `i` as valid.
- `tkeep` must be contiguous from byte lane 0. In other words, tkeep must be contiguous.
- Only the final beat may be partial.
- A non-empty stream must end with exactly one beat where `tlast=1`.
- A zero-length stream has no beats; the length register is the only indication
  that the phase is empty.
- The accumulated valid-byte count must exactly match the CSR length for that
  stream phase.
- Data after a final beat is a stream protocol error.

Examples for a 128-bit stream:

| Payload bytes in beat | Valid `tkeep` |
| ---: | --- |
| 0 | no beat for empty stream |
| 1 | `16'h0001` |
| 8 | `16'h00ff` |
| 16 | `16'hffff` |

`16'h0101`, `16'h8000`, and any other non-contiguous mask are invalid.

## Error behavior

The streaming frontend must raise `ASCON_ERROR_STREAM_PROTOCOL` for:

- non-contiguous `tkeep`;
- partial non-final beats;
- `tlast` before the programmed byte count is reached;
- reaching the programmed byte count without `tlast`;
- receiving bytes after the programmed byte count;
- wrong `tuser` for the active stream phase.

The AEAD backend must raise `ASCON_ERROR_BAD_LENGTH` for unsupported algorithmic
length combinations and `ASCON_ERROR_TAG_INVALID` when authenticated decryption
fails.

## Decryption release policy

Encryption may stream ciphertext immediately.

Decryption must not expose unauthenticated plaintext by default.  The first RTL
backend should therefore use a bounded buffer-until-verify policy:

1. receive AD and ciphertext;
2. compute and compare the tag in constant time;
3. release plaintext only if the tag is valid;
4. suppress plaintext and raise authentication failure if the tag is invalid.

A later SoC/DMA backend may implement a quarantine buffer, where plaintext is
written to temporary memory and committed only after tag verification.

## First RTL milestone

The first reusable RTL block is not the full ASCON engine.  It is the stream
framer:

```text
AXI Stream beats
    -> validate kind, keep, last, and byte count
    -> emit fixed-width data blocks with valid-byte count and final flag
```

The full AEAD128 streaming encryption core must be tested against the Python
`ascon_hwmodel.aead_stream` oracle.
