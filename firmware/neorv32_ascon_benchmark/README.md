# NEORV32 ASCON benchmark firmware

This firmware is the first end-to-end benchmark harness for the accelerator ABI.
It compares:

1. software `Ascon-AEAD128` using the portable C reference in `firmware/ascon_ref`, and
2. hardware `Ascon-AEAD128` through the frozen accelerator driver in `firmware/ascon_accel`.

The benchmark is intended to run on a NEORV32 SoC image that includes the
`neorv32_cfs` ASCON wrapper. The accelerator is addressed at the NEORV32 CFS
base address `0xffeb0000`.

## Build

From this directory:

```sh
make NEORV32_HOME=/path/to/neorv32 clean_all exe
```

The Makefile reuses the NEORV32 software build system and compiles:

- `main.c`
- the split ASCON accelerator driver
- the portable software ASCON-AEAD128 reference

## What it prints

The firmware prints over UART:

- accelerator ABI version and capabilities
- software ciphertext/tag
- hardware ciphertext/tag
- software cycle count
- hardware cycle count
- speedup scaled by 1000
- pass/fail status

The acceptance criterion for this project is:

```text
hardware_cycles < software_cycles
```

for every mode that the hardware advertises as supported.

## Stream-native backend smoke test

Before wiring a real NEORV32 MMIO-to-AXI-stream bridge or DMA frontend, run the
host-side firmware stream benchmark from the repository root:

```sh
make firmware-stream-ref-bench
```

That target compiles the normal C driver against the AXI-stream reference
emulator and checks the same encrypt/decrypt/tag-failure sequencing that the
NEORV32 stream-native benchmark will use. It is not a replacement for a board
run; it is the pre-board validation step for the stream data-plane path.
