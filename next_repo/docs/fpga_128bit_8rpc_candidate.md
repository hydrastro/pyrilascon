# FPGA 128-bit AXI Stream + 8 rounds/cycle candidate

This document describes the next FPGA throughput candidate after the 128-bit AXI Stream / 4-rounds-per-cycle target.

## Goal

Preserve the final FPGA-oriented interface:

- CSR/MMIO control plane;
- 128-bit AXI Stream data plane;
- 16-bit `tkeep` final-byte mask;
- AEAD128 encryption/decryption KAT flow;
- decrypt plaintext is only released after tag verification.

while increasing permutation throughput:

| permutation | 4RPC candidate | 8RPC candidate |
|---|---:|---:|
| p8 | 2 cycles | 1 cycle |
| p12 | 3 cycles | 2 cycles |

## Board target

```bash
nix develop
cd boards/tangnano9k/ascon_aead128_axis128_8rpc
make clean
make tools
make
make prog-sram
```

Expected LEDs:

| LED | Meaning |
|---|---|
| LED0 | heartbeat |
| LED1 | encryption KAT passed |
| LED2 | decryption KAT passed |
| LED3 | failure |
| LED4 | test completed |
| LED5 | final pass |

Good result: LED1, LED2, LED4, LED5 on; LED3 off; LED0 blinking.

## Implementation note

A p12 permutation cannot be implemented as two identical 8-round chunks. The 8RPC backend uses:

- first p12 cycle: 8 rounds, constants 4..11;
- second p12 cycle: 4 rounds, constants 12..15;
- p8 cycle: 8 rounds, constants 8..15.

Therefore `ascon_round8_comb` has a `round_count_i` input and can apply either 4 or 8 rounds.

This is still a candidate milestone. If it fails timing on Tang Nano 9K, the result does not invalidate the final high-throughput FPGA architecture; it means this small FPGA needs either 4RPC or registered pipeline stages.
