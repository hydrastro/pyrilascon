# NEORV32 stream board manifest

The stream-native NEORV32/Tang Nano 9K path now has a single board-facing
manifest:

```text
boards/tangnano9k/neorv32_stream_axis_mmio/manifest.json
```

This file is the handoff contract between the ASCON accelerator repo and the
external NEORV32/Gowin board project. It records the RTL file list, CFS wrapper,
firmware build mode, and memory map that belong together.

## What the manifest freezes

```text
CFS base + 0x000..0x0ff -> frozen ASCON CSR/MMIO ABI
CFS base + 0x100..0x1ff -> CPU-driven AXI-stream MMIO bridge
```

For the default NEORV32 CFS base this means:

```text
ASCON_ACCEL_BASE_ADDR           = 0xFFEB0000u
ASCON_ACCEL_AXIS_MMIO_BASE_ADDR = 0xFFEB0100u
```

The matching firmware build mode is:

```sh
make neorv32-stream-build-firmware
```

The matching ASCON CFS file list is:

```text
rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f
```

## Local inspection

Print the manifest from the repository root:

```sh
python tools/print_neorv32_stream_board_manifest.py
```

Validate that all referenced repository paths exist and that the expected memory
map is internally consistent:

```sh
python tools/print_neorv32_stream_board_manifest.py --check
```

The board target directory also exposes convenience targets:

```sh
cd boards/tangnano9k/neorv32_stream_axis_mmio
make manifest
make check
make memory-map
```

## Intended bring-up order

1. Run the existing Python/RTL simulations, especially the integrated stream
   AXI-MMIO system simulation.
2. Build the NEORV32 firmware with `USE_CFS_AXIS_MMIO=1`.
3. Integrate `rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd` as the CFS
   implementation in the NEORV32 SoC project.
4. Include the Verilog sources from
   `rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f`.
5. Synthesize/place/route for Tang Nano 9K.
6. Program SRAM and capture UART benchmark output.
7. Compare software cycles, hardware cycles, and speedup.

This step is still a scaffold: it does not vendor the full NEORV32 SoC or Gowin
project into this repository.
