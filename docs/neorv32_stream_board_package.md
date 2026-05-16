# NEORV32 stream board build package

The stream-native Tang Nano 9K / NEORV32 target now has a reproducible build
handoff package generator. The package is intentionally not a vendor project;
it is the deterministic set of metadata, source lists, firmware flags, and
bring-up commands required to wire the ASCON stream CFS wrapper into an upstream
NEORV32 board build.

Generate it from the repository root with:

```sh
make neorv32-stream-board-package
```

or from the board scaffold directory with:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio package
```

The default output directory is:

```text
build/neorv32_stream_axis_mmio/package
```

## Generated files

The package contains:

```text
README.md
manifest.json
preflight.json
package.json
memory_map.json
rtl_sources_all.f
rtl_sources_verilog.f
rtl_sources_vhdl.f
firmware/neorv32_stream_defines.mk
firmware/ascon_stream_axis_mmio_config.h
commands.sh
```

The split RTL source lists exist because the target is mixed-language:

- Verilog sources implement the ASCON CSR block, AXI-MMIO bridge, and stream
  AEAD backend.
- The VHDL source is the NEORV32 `neorv32_cfs` replacement wrapper and should be
  compiled into the NEORV32 library in place of the stock CFS template.

## Firmware constants

The generated firmware files freeze the single-CFS-window stream map:

```c
#define ASCON_BENCH_USE_AXIS_MMIO 1
#define ASCON_ACCEL_BASE_ADDR 0xFFEB0000u
#define ASCON_ACCEL_AXIS_MMIO_BASE_ADDR 0xFFEB0100u
```

The benchmark build mode remains:

```sh
make neorv32-stream-build-firmware
```

## Validation

The package generator validates the manifest, preflight plan, generated file
set, memory map, split RTL source lists, and firmware address definitions.
Run the package check directly with:

```sh
python tools/prepare_neorv32_stream_board_build.py --check \
  --out build/neorv32_stream_axis_mmio/package
```

`commands.sh` inside the package records the expected pre-board command sequence:
manifest check, preflight check, NEORV32 CFS integration tests, integrated system
simulation, and firmware build when `NEORV32_HOME` is set.

## Dry-run build plan

After generating the package, run:

```sh
make neorv32-stream-board-build-plan
```

This validates the generated package and writes JSON/Markdown build-plan reports under `build/neorv32_stream_axis_mmio/`.
