# Buffered streaming AEAD128 decrypt backend

`rtl/stream/ascon_aead128_stream_decrypt_buffered.v` is the conservative decrypt-side companion to the stream-native encryption backend.

## Why decrypt is buffered

Authenticated decryption must not expose plaintext until the tag has been verified. A truly unbounded AXI-stream decrypt backend cannot both suppress plaintext and avoid storage: it must either release speculative plaintext, write to an external quarantine region, or use a bounded internal buffer.

This backend chooses the safe first milestone:

```text
ciphertext stream in
    -> decrypt into internal quarantine buffer
    -> compute tag
    -> compare against expected_tag_i
    -> release plaintext stream only if the tag matches
```

## Interface policy

The input stream follows the same AD-then-TEXT contract as encryption:

```text
AD packet first, then ciphertext packet
```

The output stream is plaintext with `tuser = ASCON_AXIS_USER_TEXT`, but output is delayed until after authentication succeeds.

If authentication fails:

```text
m_axis_tvalid remains low
plain_buf_q is cleared
tag_valid_o = 0
error_o = 1
error_code_o = ASCON_ERROR_TAG_INVALID
```

## Bound

The module has an explicit `MAX_TEXT_BYTES` parameter. The default is 1024 bytes. This is intentionally not advertised as unbounded. A later DMA/quarantine backend should replace the internal buffer while preserving the same no-plaintext-before-authentication policy.

## Current boundary

Implemented:

- AEAD128 decrypt only;
- 128-bit AXI Stream data width;
- contiguous low-byte `tkeep` validation;
- exact AD/text length validation;
- constant-time-style reduction comparison over the computed tag;
- plaintext release only after tag verification.

Not implemented yet:

- unbounded decrypt through external DMA quarantine;
- speculative plaintext release mode;
- AEAD128a / AEAD128pq decrypt variants;
- real top-level mux between encrypt/decrypt stream backends.
