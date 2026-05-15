# NEORV32 ASCON Accelerator Demo Firmware

This directory contains the first firmware demo for the pyrilascon accelerator
ABI. It is written for NEORV32 CFS integration and assumes the ASCON accelerator
is visible at the CFS base address:

```c
#define ASCON_ACCEL_BASE_ADDR 0xFFEB0000u
```

## Current behavior

`main.c`:

1. initializes the NEORV32 runtime and UART0,
2. probes `ABI_VERSION` and `CAPABILITIES`,
3. checks that `AEAD128` is supported,
4. writes key, nonce, associated data, and plaintext through the portable driver,
5. starts encryption,
6. prints ciphertext, tag, and hardware cycle count.

## Build

Point `NEORV32_HOME` at a checked-out NEORV32 repository:

```bash
make NEORV32_HOME=/path/to/neorv32 clean_all exe
```

The Makefile uses NEORV32's normal software build system and adds the portable
accelerator driver from `firmware/ascon_accel`.

## Hardware requirement

This firmware requires the CFS replacement:

```text
rtl/neorv32/neorv32_cfs_ascon.vhd
```

plus the Verilog accelerator backend listed in:

```text
rtl/neorv32/ascon_cfs_file_list.f
```

The standalone Tang Nano 9K LED tests do not use this firmware. They are direct
RTL self-tests. This firmware is for the next milestone: running ASCON through a
NEORV32 CPU and printing the result over UART.
