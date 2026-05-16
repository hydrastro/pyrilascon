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


## Stream-native build

To build the same benchmark for the new stream-native AEAD128 path, enable the
CPU-driven MMIO-to-AXI-stream transport:

```sh
make NEORV32_HOME=/path/to/neorv32 USE_AXIS_MMIO=1 clean_all exe
```

This compiles `ascon_accel_axis_mmio_transport.c`, sets
`ASCON_BENCH_USE_AXIS_MMIO=1`, programs the frozen accelerator CSR block at
`ASCON_ACCEL_BASE_ADDR`, and sends/receives 128-bit AXI-stream beats through the
separate bridge window at `ASCON_ACCEL_AXIS_MMIO_BASE_ADDR`. The UART log prints
`DATA PLANE : AXI_STREAM_MMIO` plus TX/RX beat counters so board bring-up can
confirm that the firmware actually exercised the stream path.

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


## CPU-driven stream bridge path

The repository now includes a concrete firmware transport for a small
MMIO-to-AXI-stream bridge: `ascon_accel_axis_mmio_transport.h/.c`. A NEORV32
platform can keep `ASCON_ACCEL_BASE_ADDR` pointed at the frozen accelerator CSR
map and set `ASCON_ACCEL_AXIS_MMIO_BASE_ADDR` to a separate stream bridge window.
Then the benchmark can select `ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL`,
install the MMIO bridge transport callbacks, and exercise the stream-native
`ascon_accel_stream_aead128_top` without DMA.

This is intended as the next board bring-up step after the host-side
`make firmware-stream-ref-bench` smoke test. DMA can replace only the transport
later; the benchmark API and accelerator ABI remain stable.

## RTL bridge target

The matching RTL bring-up target for `USE_AXIS_MMIO=1` is:

```text
rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v
```

It exposes two simple MMIO windows: the frozen ASCON CSR window and the AXI
stream bridge window consumed by `ascon_accel_axis_mmio_transport.c`.

## Single-CFS-window stream wrapper build

For the stream-native NEORV32 CFS wrapper in:

```text
rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd
```

build the benchmark with:

```sh
make NEORV32_HOME=/path/to/neorv32 USE_CFS_AXIS_MMIO=1 clean_all exe
```

This maps the frozen CSR window to `0xffeb0000` and the CPU-driven AXI-stream
bridge window to `0xffeb0100`.  It is the preferred firmware build for the
single-CFS-window board bring-up target.
