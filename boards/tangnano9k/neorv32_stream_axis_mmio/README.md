# Tang Nano 9K NEORV32 stream-native ASCON target

This directory is the board-facing scaffold for the stream-native ASCON AEAD128
accelerator behind NEORV32 CFS. It does not replace the upstream NEORV32 Gowin
project files; it records the ASCON-specific RTL, firmware mode, and memory map
that must be used when wiring the CFS block into the SoC.

## Manifest

The canonical build contract is:

```text
boards/tangnano9k/neorv32_stream_axis_mmio/manifest.json
```

Print it from the repository root with:

```sh
python tools/print_neorv32_stream_board_manifest.py
```

or from this directory with:

```sh
make manifest
make check
```

## Memory map

For the default NEORV32 CFS base:

```text
0xFFEB0000..0xFFEB00FF  frozen ASCON CSR/MMIO ABI
0xFFEB0100..0xFFEB01FF  CPU-driven AXI-stream MMIO bridge
```

The firmware benchmark build mode `USE_CFS_AXIS_MMIO=1` selects this map.

## Preflight

Generate the machine-readable bring-up plan from the repository root with:

```sh
make neorv32-stream-board-preflight
```

or from this directory with:

```sh
make preflight
```

The generated JSON is written to `build/neorv32_stream_axis_mmio/preflight.json`.


## Build package

Generate the deterministic board handoff package from the repository root with:

```sh
make neorv32-stream-board-package
```

or from this directory with:

```sh
make package
make uart-report LOG=/path/to/uart.log
```

The package is written to `build/neorv32_stream_axis_mmio/package` and contains
the manifest, preflight plan, split Verilog/VHDL source lists, firmware defines,
memory map, and a command sketch for pre-board validation.

## Firmware smoke build

```sh
make firmware
```

which resolves a usable NEORV32 checkout with `tools/ensure_neorv32_checkout.py` and then delegates to the firmware Makefile.  The default checkout is project-local: `external/neorv32`.

## RTL inputs

Use this file list for the ASCON CFS replacement:

```text
rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f
```

The wrapper entity is still named `neorv32_cfs`, so it is intended to replace
or override the NEORV32 CFS implementation during the SoC build.

## Pre-board validation

Before starting synthesis/board work, run:

```sh
python -m pytest -q tests/test_neorv32_stream_cfs_integration.py
python -m pytest -q tests/test_stream_axis_mmio_system_sim.py
make stream-axis-mmio-system-sim
```

The system simulation proves the frozen CSR window, AXI-MMIO bridge, stream
AEAD backend, tag registers, and RX FIFO work together for FIFO-fit messages.

## Dry-run build plan

After generating the package, validate the board handoff with:

```sh
make build-plan
```

This writes `build/neorv32_stream_axis_mmio/build_plan.json` and `.md` from the repository root.


## Gowin / NEORV32 handoff

Generate the board handoff directory with:

```sh
make gowin-handoff
```

This writes `build/neorv32_stream_axis_mmio/gowin_handoff` from the repository
root.  The handoff contains separated Verilog/VHDL source lists, firmware defines,
and guarded helper scripts for the first real Tang Nano integration attempt.
