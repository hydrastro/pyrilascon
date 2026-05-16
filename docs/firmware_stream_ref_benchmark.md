# Firmware stream reference benchmark

This benchmark is a host-side smoke test for the stream-native firmware path.
It runs the normal C driver against the AXI-stream reference emulator, not
against a synthesizable RTL simulator.

The goal is to validate the software/ABI sequence that the NEORV32 benchmark
will use once a real stream transport bridge or DMA frontend is connected:

```text
ascon_accel_benchmark_encrypt/decrypt
    -> MMIO control/status register image
    -> AXI-stream send/recv callbacks
    -> AXI-stream reference emulator
    -> portable C Ascon-AEAD128 reference
```

## Running it

From the repository root:

```sh
make firmware-stream-ref-bench
```

or directly:

```sh
python tools/run_firmware_stream_ref_benchmark.py --json
```

The tool builds a temporary C executable with `gcc`, runs four message shapes,
and emits a JSON report.

## Cases

The current benchmark covers:

- empty AD and empty plaintext;
- empty AD and short plaintext;
- short AD and a partial final plaintext block;
- one full AD block and two full plaintext blocks.

Each case checks:

- firmware encryption succeeds;
- ciphertext and tag match the portable reference;
- firmware decrypt succeeds and releases plaintext only after authentication;
- invalid decrypt tag returns `ASCON_ACCEL_ERR_TAG_INVALID`;
- invalid decrypt tag suppresses plaintext output;
- encryption and decryption benchmark cycle deltas are nonzero.

## Why this exists before the board demo

The stream-native SoC top uses MMIO for control and AXI Stream for payload.
The NEORV32 CPU cannot drive that payload path directly until the SoC includes
an MMIO-to-AXI-stream bridge, DMA engine, or another concrete transport.

This host benchmark validates the firmware sequencing and benchmark plumbing
against a deterministic AXI-stream reference emulator first. After the bridge or
DMA frontend exists, the NEORV32 benchmark can reuse the same driver calls and
replace only the transport callbacks.
