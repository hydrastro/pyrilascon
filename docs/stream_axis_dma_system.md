# Stream AEAD AXI-stream DMA front-end system

This milestone adds an autonomous, descriptor-driven DMA front-end for the
stream-native AEAD-128 backend, plus an integration-level RTL cosimulation for:

```text
ascon_accel_stream_aead128_axis_dma_system
```

It is the data-plane counterpart of the CPU-driven AXI-MMIO bridge documented in
`stream_axis_mmio_system_simulation.md`. The MMIO bridge makes the processor
push and pop every 128-bit beat, so a long payload costs `O(length)` loads and
stores and is capped by the small bridge RX FIFO (four output beats by default).
The DMA front-end instead takes a compact descriptor and moves the whole
encryption payload itself, so firmware programs a handful of registers and one
`GO` bit and then waits for `DONE` (or an interrupt).

## What the DMA front-end is

```text
DMA descriptor MMIO window
  -> AD/TEXT source addresses, lengths, destination address, GO/IRQ/CLEAR

memory master port (single outstanding)
  -> fetches AD and plaintext words, writes ciphertext words back

stream AEAD128 backend
  -> encryption core and tag generation (unchanged, frozen ABI)
```

The control plane is unchanged: key, nonce, lengths, mode, `CONTROL.START`, and
the resulting tag are still driven through the frozen ASCON CSR ABI. The DMA
block sits only in front of the backend's AXI-stream ports and automates the
*data* movement for **encryption**. Buffered authenticated decryption keeps the
CPU-driven transport, because its burst-at-the-end dataflow differs from the
streaming encrypt path; decrypt-side DMA is left as future work.

### Descriptor register map

The descriptor block is a separate MMIO window from the frozen CSR map. Byte
offsets from the DMA base address:

```text
0x00 AD_ADDR     source address of associated data
0x04 AD_LEN      associated-data length in bytes
0x08 TEXT_ADDR   source address of the plaintext
0x0c TEXT_LEN    plaintext length in bytes
0x10 DST_ADDR    destination address for the ciphertext
0x14 CTRL        bit0 GO (start), bit8 IRQ_EN, bit16 CLEAR
0x18 STATUS      bit0 BUSY, bit1 DONE, bit2 ERROR, bits[15:8] output beats
0x1c OUT_BYTES   ciphertext bytes written back on completion
```

Descriptor writes and `CLEAR` are accepted only while the engine is idle.
`CLEAR` drops a latched `DONE`/`ERROR` from a previous transfer and leaves the
descriptor registers intact. `GO` latches the descriptor into the working
counters and starts the transfer. Addresses are the addresses seen by the DMA
memory master port; the backing store is 32-bit, little-endian, and word
addressed, so all three buffer addresses must be 4-byte aligned (the firmware
driver rejects non-aligned descriptors before touching the bus).

## Strict 1:1 serialization

The encrypt backend gates its text input `tready` on its output not being
valid, so a new plaintext beat may only be presented once the previous
ciphertext beat has been accepted. The DMA engine honors this with a single
`pending_out` token: after presenting an input beat it will not stage the next
one until the matching output beat has been drained and written back. This keeps
exactly one beat in flight and makes the streaming behavior independent of
payload length — there is no internal output FIFO to overflow, which is the
limitation the CPU bridge has.

Per-segment `tlast` is asserted combinationally on the last beat of each segment
(the final AD beat and, separately, the final text beat), matching the backend's
`ad_length_error` / `text_length_error` checks. An earlier revision latched the
AD `tlast` a cycle too late and tripped a length error on the first AD beat;
driving `tlast` directly from the running byte counts fixed it.

## Cosimulation scope

`tools/run_stream_axis_dma_system_vector.py` builds the same Python golden vector
used by the rest of the streaming suite (`axis_aead128_encrypt`), generates a
self-contained testbench with an embedded synchronous memory model (always-ready
acceptance, one-cycle read response, byte-strobed writes, AD and plaintext
preloaded into the backing store), and drives the full SoC-facing stack:

- program the frozen CSR control plane (`CLEAR`, mode, lengths, key, nonce,
  `CONTROL.START`);
- program the DMA descriptor (`CLEAR`, source/destination addresses, lengths)
  and pulse `GO`;
- wait for DMA `STATUS.DONE` and CSR `STATUS.DONE`;
- read the ciphertext back from the destination region of the memory model and
  the tag from the frozen CSR tag registers.

A run is counted as matched only when the ciphertext and tag equal the golden
values, `ERROR_CODE` is zero, `OUT_BYTES` equals the plaintext length, both
`DONE` flags are set, and no `ERROR` is raised.

The integrated cosimulation covers empty payloads, short partial final blocks,
multi-beat AD (up to seven beats), and multi-beat plaintext up to the backend's
1024-byte maximum (64 output beats). Reported cycle counts scale linearly with
payload length (about 82 cycles empty to roughly 1170 cycles for 1024 bytes),
confirming that the engine streams beat by beat. The 64-beat case is the
headline result: it is far beyond the four-beat CPU bridge RX FIFO, so it could
not be driven by the MMIO bridge without an interleaved firmware pump, yet the
DMA path streams it to memory with one beat in flight throughout.

The standalone backend simulations remain the proof of the unbounded stream and
buffered-decrypt behavior; this system cosimulation proves the DMA wiring,
descriptor protocol, and ciphertext writeback are correct.

## Firmware driver

`firmware/ascon_accel/ascon_accel_axis_dma_transport.{c,h}` provides a
descriptor-oriented one-shot driver (distinct from the beat-by-beat MMIO
transport vtable). It programs the descriptor, pulses `GO` (optionally enabling
the completion interrupt), and polls `STATUS` for `DONE`/`ERROR` with a timeout,
returning the number of ciphertext bytes written. The control plane
(key/nonce/`CONTROL.START`/tag) is still issued through the existing
`ascon_accel` CSR API, exactly as the cosimulation sequences it.

## Manual command

With Icarus Verilog available:

```bash
make stream-axis-dma-system-sim
```

Equivalent direct command using a multi-beat plaintext:

```bash
python tools/run_stream_axis_dma_system_vector.py \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex aabbccddeeff \
  --plaintext-hex 000102030405060708090a0b0c0d0e0f101112
```

Without a simulator, use dry-run mode to inspect the golden vector and the
generated testbench:

```bash
python tools/run_stream_axis_dma_system_vector.py \
  --dry-run --include-testbench \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --nonce-hex 101112131415161718191a1b1c1d1e1f \
  --ad-hex aabbccddeeff \
  --plaintext-hex 000102030405060708090a0b0c0d0e0f101112
```
