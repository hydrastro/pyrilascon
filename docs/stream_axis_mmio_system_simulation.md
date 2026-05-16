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

This is deliberately narrower than the standalone stream-backend simulations.
Those tests already prove multi-beat stream encryption/decryption behavior.  The
system smoke test proves that the SoC-facing wiring is correct:

- CSR register programming reaches the stream backend;
- `CONTROL.START` starts the stream backend before payload beats arrive;
- the AXI-MMIO bridge can feed AD/TEXT beats into the backend;
- ciphertext can be captured through the bridge RX register;
- generated tags are latched back into the frozen ABI tag registers;
- `STATUS.DONE`, `STATUS.ERROR`, and `ERROR_CODE` reflect the completed operation.

## Scope

The current integrated simulation covers zero- or one-beat plaintext vectors.
That is enough to validate the full CSR + bridge + stream backend interconnect
without introducing a large RX FIFO or a full-duplex firmware pump.

The CPU-driven AXI-MMIO bridge contains one RX holding register. For real
multi-beat CPU-driven transfers, firmware must either interleave output draining
with text streaming or the system must use a deeper FIFO/DMA front end. The
standalone stream backend remains unbounded; this limitation belongs to the
small CPU bridge, not to the AEAD stream core.

## Manual command

With Icarus Verilog available:

```bash
make stream-axis-mmio-system-sim
```

Equivalent direct command:

```bash
python tools/run_stream_axis_mmio_system_vector.py \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex aabbccddeeff \
  --plaintext-hex 0001020304050607
```

Without a simulator, use dry-run mode to inspect the golden vector and generated
testbench:

```bash
python tools/run_stream_axis_mmio_system_vector.py \
  --dry-run --include-testbench \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex aabbccddeeff \
  --plaintext-hex 0001020304050607
```
