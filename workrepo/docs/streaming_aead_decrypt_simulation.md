# Buffered AEAD128 Decrypt Simulation Flow

`tools/run_stream_decrypt_vector.py` is the behavioral simulation harness for
`rtl/stream/ascon_aead128_stream_decrypt_buffered.v`.

The tool starts from a plaintext-oriented test case, encrypts it with the Python
stream oracle to obtain ciphertext and the correct tag, then feeds AD and
ciphertext beats to the RTL buffered decrypt backend.  This keeps decrypt tests
paired with the same golden model used by the streaming encryption backend.

## Valid tag path

This section covers the valid tag simulator path.

A valid-tag run must satisfy all of the following:

- the RTL generated tag equals the Python-computed tag;
- `tag_valid_o` is asserted;
- `error_o` is low and `error_code_o` is `ASCON_ERROR_NONE`;
- plaintext beats are emitted only after authentication succeeds;
- emitted plaintext bytes exactly match the original plaintext.

Example:

```bash
PYTHONPATH=. python tools/run_stream_decrypt_vector.py \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex aabbccddeeff \
  --plaintext-hex 000102030405060708090a0b0c0d0e0f101112
```

## Corrupt tag path

This section covers the corrupt tag simulator path and plaintext suppression.

A corrupt tag run verifies plaintext suppression.  The RTL must still compute and
report the real generated tag, but it must not emit any plaintext beat.

Example:

```bash
PYTHONPATH=. python tools/run_stream_decrypt_vector.py \
  --corrupt-tag \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex 6d65746164617461 \
  --plaintext-hex 73656372657420706c61696e74657874
```

Expected corrupt-tag behavior:

- `tag_valid_o = 0`;
- `error_o = 1`;
- `error_code_o = ASCON_ERROR_TAG_INVALID`;
- no `OUT_BEAT` lines are produced.

## Simulator requirements

The pytest tests run real RTL simulation only when both `iverilog` and `vvp` are
available.  Without those tools, simulator-dependent tests are skipped while the
golden-vector and generated-testbench tests still run.

Use `--dry-run` to inspect the generated golden vector without invoking the
simulator.
