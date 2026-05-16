# FPGA 128-bit AXI Stream + 4-rounds-per-cycle candidate

This milestone is the first concrete move from the working AXI Stream smoke test
toward the maximum-throughput FPGA architecture.

The design keeps the frozen CSR/MMIO ABI for configuration and status, but uses a
128-bit AXI Stream-style data plane and a four-rounds-per-cycle permutation slice.

## Intent

This is not the final fully pipelined, multi-context FPGA engine. It is an
intermediate candidate with two important properties:

1. the external payload interface is 128-bit wide and uses `tkeep` as the
   streaming final byte mask;
2. the permutation backend reduces p8/p12 latency by computing four Ascon rounds
   combinationally per cycle.

## Latency model

| Permutation | 1 round/cycle | 4 rounds/cycle |
|---|---:|---:|
| p8 | 8 cycles | 2 cycles |
| p12 | 12 cycles | 3 cycles |

The current small-message backend still buffers inputs internally, so this is not
full streaming throughput yet. The purpose of this step is to validate timing,
resource cost, and board behavior for the 4RPC permutation slice and 128-bit
stream ABI before replacing the backend with a true streaming/multi-context core.

## Board target

```bash
nix develop
cd boards/tangnano9k/ascon_aead128_axis128_4rpc
make clean
make tools
make
make prog-sram
```

Expected pass: LED0 blinking, LED1/LED2/LED4/LED5 on, LED3 off.

## Next candidates

If this fits and passes, the next FPGA candidates are:

1. 8 rounds per cycle, 128-bit AXI Stream;
2. fully pipelined p8/p12 permutation with context interleaving;
3. M permutation pipelines with N contexts per pipeline.
