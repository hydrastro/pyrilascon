# Tang Nano 9K ASCON-AEAD128 AXI Stream 128-bit 4RPC target

This is the first FPGA high-throughput candidate after the AXI Stream smoke test.

It keeps the frozen CSR/MMIO control plane, but uses a 128-bit AXI Stream-style
payload interface and a four-rounds-per-cycle permutation backend:

- p8 latency: 2 cycles
- p12 latency: 3 cycles
- stream `tkeep`: 16-bit final-byte mask
- decryption output is buffered until tag verification succeeds

The current backend is still small-message bounded and internally bridges to the
existing register-buffered core. It is a migration target toward the final fully
streaming, multi-context FPGA architecture.

## Build and program

```bash
nix develop
cd boards/tangnano9k/ascon_aead128_axis128_4rpc
make clean
make tools
make
make prog-sram
```

## LEDs

The Tang Nano 9K LEDs are active-low.

| LED | Meaning |
|---|---|
| LED0 | heartbeat |
| LED1 | encryption KAT through 128-bit AXIS passed |
| LED2 | decryption KAT through 128-bit AXIS passed |
| LED3 | failure indicator |
| LED4 | test completed |
| LED5 | final pass |

Expected pass condition: LED0 blinks, LED1/LED2/LED4/LED5 are on, LED3 is off.
