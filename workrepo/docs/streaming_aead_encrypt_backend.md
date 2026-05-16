# AEAD128 Streaming Encryption Backend

`rtl/stream/ascon_aead128_stream_encrypt.v` is the first RTL backend that follows
`docs/streaming_aead_contract.md` without using whole-message AD/plaintext
buffers.

## Scope

Implemented now:

- NIST Ascon-AEAD128 encryption only.
- 128-bit AXI4-Stream input and output beats.
- One Ascon round per cycle.
- AD packet first, then plaintext packet.
- `tuser = ASCON_AXIS_USER_AD` for AD and `tuser = ASCON_AXIS_USER_TEXT` for plaintext.
- Ciphertext output as `ASCON_AXIS_USER_TEXT`.
- Local AXI beat validation for each AD/TEXT phase; `ascon_axis_framer` remains available as a standalone reusable validator.
- Unbounded encryption: the backend never needs to store the complete AD or
  plaintext message.

Intentionally not implemented in this backend:

- Authenticated decrypt.
- DMA quarantine / plaintext commit protocol.
- Multi-context scheduling.
- 4RPC/8RPC or fully-pipelined permutation variants.
- A full frozen-ABI top-level wrapper replacing the older bounded AXI top.

## Control-plane contract

The control plane still supplies:

- `mode_i = ASCON_MODE_AEAD128`
- `decrypt_i = 0`
- `key_i`
- `nonce_i`
- `ad_len_i`
- `text_len_i`
- `custom_len_i = 0`
- `out_len_i = 0`

Unsupported mode, decrypt requests, non-zero custom length, non-zero out length,
or non-128-bit stream configuration raise an error instead of silently changing
semantics.

## Stream order

The input data plane is deliberately phase-ordered:

```text
START
  initialize ASCON state
  receive AD stream packet, if ad_len_i > 0
  domain separate
  receive plaintext stream packet, if text_len_i > 0
  emit ciphertext stream beats while processing plaintext
  finalize
  expose generated tag
DONE
```

Zero-length AD and zero-length plaintext are represented by the length registers;
they do not require dummy AXI beats.

## Padding behavior

For AD:

- every full 128-bit AD block is absorbed and followed by p8;
- if the final AD beat is partial, it is padded and followed by p8;
- if AD length is an exact multiple of 16 bytes, an additional empty padded AD
  block is absorbed and followed by p8;
- if AD length is zero, no AD padding block is absorbed.

For plaintext:

- every full plaintext block emits one full ciphertext beat and is followed by p8;
- if the final plaintext beat is partial, it emits one partial ciphertext beat and
  finalization starts immediately;
- if plaintext length is an exact multiple of 16 bytes, an additional empty padded
  plaintext block is applied after the final full ciphertext beat and before
  finalization;
- if plaintext length is zero, only the empty padded plaintext block is applied.

## Why this is a separate backend

The older AXI wrappers freeze the external interface but still serialize into the
small bounded MMIO backend. This module is the first step toward the actual FPGA
architecture: a stream-native datapath that consumes validated beats and performs
ASCON scheduling incrementally.
