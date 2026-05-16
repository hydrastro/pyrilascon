# Stream AEAD AXI-MMIO system simulation

This milestone adds an integration-level RTL smoke test for:

```text
ascon_accel_stream_aead128_axis_mmio_system
```

The testbench drives the complete bring-up-facing RTL stack through the same two
MMIO windows that NEORV32 firmware will use:

```text
CSR/MMIO window
  -> frozen ASCON control/status/key/nonce/tag ABI

AXI-MMIO bridge window
  -> CPU-driven 128-bit AXI-stream TX/RX beats

stream AEAD128 backend
  -> encryption core and tag generation
```

The standalone stream-backend simulations prove unbounded stream encryption and
buffered authenticated decrypt behavior. The system smoke test proves the
SoC-facing wiring is correct:

- CSR register programming reaches the stream backend;
- `CONTROL.START` starts the stream backend before payload beats arrive;
- the AXI-MMIO bridge can feed AD/TEXT beats into the backend;
- ciphertext can be captured through the bridge RX FIFO and exposed via `RX_*`;
- generated tags are latched back into the frozen ABI tag registers;
- `STATUS.DONE`, `STATUS.ERROR`, and `ERROR_CODE` reflect the completed operation.

## Scope

The integrated simulation now covers vectors that fit inside the bridge RX FIFO.
The default FIFO depth is four 128-bit output beats, which is enough to verify
multi-beat CPU-driven bring-up without adding DMA.

The stream backend itself remains the unbounded path. The FIFO depth only limits
how much output the small CPU bridge can absorb while firmware is still sending
input beats. Larger real systems should use either a deeper bridge FIFO, an
interleaved firmware pump, or DMA.

## Manual command

With Icarus Verilog available:

```bash
make stream-axis-mmio-system-sim
```

Equivalent direct command using a multi-beat plaintext that fits in the default
RX FIFO:

```bash
python tools/run_stream_axis_mmio_system_vector.py \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex aabbccddeeff \
  --plaintext-hex 000102030405060708090a0b0c0d0e0f101112
```

Without a simulator, use dry-run mode to inspect the golden vector and generated
testbench:

```bash
python tools/run_stream_axis_mmio_system_vector.py \
  --dry-run --include-testbench \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex aabbccddeeff \
  --plaintext-hex 000102030405060708090a0b0c0d0e0f101112
```
