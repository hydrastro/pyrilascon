# Streaming AEAD128 RTL Simulation

This milestone adds a behavioral simulation harness for the stream-native
AEAD128 encryption backend. The goal is to compare the RTL implementation
against the Python golden stream model before adding decrypt, DMA, NEORV32, or
high-throughput pipeline variants.

## Flow

`tools/run_stream_encrypt_vector.py` is the single-vector runner:

1. Build the Python golden reference with
   `ascon_hwmodel.aead_stream.axis_aead128_encrypt`.
2. Pack AD and plaintext into AXI-style beats using the same `tkeep` and `tlast`
   contract as the RTL.
3. Generate a vector-specific Verilog testbench for
   `rtl/stream/ascon_aead128_stream_encrypt.v`.
4. Compile the testbench with `iverilog`.
5. Run it with `vvp`.
6. Parse emitted output beats and the generated tag.
7. Compare RTL ciphertext and tag against the Python golden ciphertext and tag.

The regular pytest suite does not require a simulator. Simulation tests are
marked optional and are skipped when `iverilog`/`vvp` are not installed. The
same tests run automatically when those tools are available in the shell.

## Manual command

Example dry run, useful when no simulator is installed:

```bash
python tools/run_stream_encrypt_vector.py \
  --dry-run \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex aabbccddeeff \
  --plaintext-hex 000102030405060708090a0b0c0d0e0f101112
```

Full RTL simulation, when Icarus Verilog is installed:

```bash
python tools/run_stream_encrypt_vector.py \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex aabbccddeeff \
  --plaintext-hex 000102030405060708090a0b0c0d0e0f101112
```

The output JSON contains:

- Python golden ciphertext;
- Python golden tag;
- RTL ciphertext;
- RTL tag;
- RTL error flags;
- cycle count;
- raw simulator lines.

## Coverage intent

The harness is intentionally focused on behavioral agreement, not performance.
It exercises:

- zero-length AD and plaintext;
- empty AD with non-empty plaintext;
- non-empty AD with empty plaintext;
- exact 16-byte block boundaries;
- multi-beat plaintext;
- partial final `tkeep` masks.

This is the correctness checkpoint before implementing authenticated decrypt or
throughput-oriented stream cores.
