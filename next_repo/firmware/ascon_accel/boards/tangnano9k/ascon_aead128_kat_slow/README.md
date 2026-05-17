# Tang Nano 9K: full Ascon-AEAD128 KAT smoke test

This target is intentionally **full AEAD128**, not just a permutation test.
It runs one fixed NIST-style Ascon-AEAD128 encryption known-answer test entirely in RTL:

- initialization
- associated-data processing
- plaintext processing
- finalization
- ciphertext/tag comparison

The datapath is deliberately slow and simple: one Ascon round per clock.
It is intended as the first complete FPGA correctness target before adding a streaming NEORV32/MMIO interface.

## Build

```sh
cd boards/tangnano9k/ascon_aead128_kat_slow
make
make prog-sram
```

## LED meaning

The Tang Nano 9K LEDs are active low.

| LED | Meaning |
| --- | --- |
| LED0 | heartbeat |
| LED1 | KAT passed |
| LED2 | KAT failed |
| LED3 | core busy |
| LED4 | core done |
| LED5 | pass and no fail |

A good run leaves LED1, LED4, LED5 on, LED2 off, and LED0 blinking.
