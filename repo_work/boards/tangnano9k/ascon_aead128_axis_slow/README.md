# Tang Nano 9K Ascon-AEAD128 AXI Stream slow smoke test

This target validates the FPGA-facing split interface:

- CSR/MMIO control plane for mode, key, nonce, lengths, start, status, and tag registers.
- AXI4-Stream-style data plane for associated data and plaintext/ciphertext words.

The cryptographic backend is still the bounded, one-round-per-cycle AEAD128 backend used by the MMIO target.  This board test is not the final high-throughput architecture; it proves the AXI Stream contract before replacing the backend with a wider/pipelined FPGA implementation.

## Build

```sh
nix develop
cd boards/tangnano9k/ascon_aead128_axis_slow
make clean
make tools
make
make prog-sram
```

## LEDs

The Tang Nano 9K LEDs are active-low.

| LED | Meaning |
| --- | --- |
| LED0 | heartbeat |
| LED1 | encryption through AXI Stream passed |
| LED2 | decryption through AXI Stream passed |
| LED3 | failure indicator |
| LED4 | test completed |
| LED5 | final pass |

Expected pass condition: LED0 blinking, LED1/LED2/LED4/LED5 on, LED3 off.
