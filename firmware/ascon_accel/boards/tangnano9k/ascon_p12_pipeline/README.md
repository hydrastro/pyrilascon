# Tang Nano 9K: Ascon-p[12] Fully Pipelined Smoke Test

This is the first "maximum-throughput-first" hardware target for the Tang Nano 9K.
It implements a 12-stage fully pipelined Ascon-p[12] permutation. After the pipeline
fills, it accepts one 320-bit state per clock and emits one 320-bit permuted state per
clock.

This is **not yet a full AEAD accelerator**. It is the high-throughput permutation
building block that the future multi-context FPGA AEAD engine will use.

## Why this architecture first?

The Tang Nano 9K has a modest but usable GW1NR-9 FPGA. The board documentation lists
8640 LUT4 logic units, 6480 flip-flops, 468 Kbits of block SRAM, and a 27 MHz onboard
clock. A fully pipelined p12 permutation is aggressive but still a realistic first
experiment on this device.

## Build

Install the open-source Gowin flow first:

- `yosys`
- `nextpnr-gowin`
- `gowin_pack`
- `openFPGALoader`

Then run:

```bash
cd boards/tangnano9k/ascon_p12_pipeline
make
make prog-sram
```

To program flash instead of SRAM:

```bash
make prog-flash
```

## LED behavior

Tang Nano 9K LEDs are active-low.

| LED | Meaning |
|---|---|
| LED0 | heartbeat |
| LED1 | `Ascon-p[12](zero_state)` self-test passed |
| LED2 | self-test failed |
| LED3 | pipeline output activity divider |
| LED4 | self-test completed |
| LED5 | pass and no fail |

Expected good result: LED1, LED4, and LED5 on, LED2 off, LED0/LED3 blinking.

## Throughput interpretation

At the board oscillator frequency of 27 MHz:

- permutation initiation interval: 1 cycle
- p12 latency: 12 cycles
- internal permutation-state throughput: `320 bits * 27 MHz = 8.64 Gbit/s`

For a future ASCON-AEAD128 multi-context engine, the useful payload rate is limited by
the 128-bit AEAD rate and mode scheduling, not by the 320-bit permutation state width.
A context-interleaved pipeline is required to keep this permutation continuously busy.
