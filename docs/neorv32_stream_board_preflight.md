# NEORV32 stream board preflight

The Tang Nano 9K NEORV32 stream target now has a machine-readable preflight
step before physical board work. The preflight tool consumes the board manifest,
checks the RTL and firmware paths, confirms the root/board Makefile targets, and
emits a JSON bring-up plan.

## Commands

From the repository root:

```sh
make neorv32-stream-board-manifest
make neorv32-stream-board-preflight
```

The preflight target writes:

```text
build/neorv32_stream_axis_mmio/preflight.json
```

You can also run the tool directly:

```sh
python tools/neorv32_stream_board_preflight.py --check
python tools/neorv32_stream_board_preflight.py --json
python tools/neorv32_stream_board_preflight.py --out build/neorv32_stream_axis_mmio/preflight.json
```

From the board scaffold directory:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio manifest
make -C boards/tangnano9k/neorv32_stream_axis_mmio check
make -C boards/tangnano9k/neorv32_stream_axis_mmio preflight
```

## NEORV32_HOME handling

The normal preflight does not require a local NEORV32 checkout. It records whether
`NEORV32_HOME` was provided and whether `sw/common/common.mk` exists. To make the
check fail unless the firmware build can run, use:

```sh
python tools/neorv32_stream_board_preflight.py \
  --neorv32-home /path/to/neorv32 \
  --require-neorv32-home \
  --check
```

## What the generated plan records

The JSON plan records:

- board identity and FPGA family;
- frozen ASCON CSR base and AXI-MMIO bridge base;
- firmware build mode `USE_CFS_AXIS_MMIO=1`;
- RTL file list and expanded source list;
- root and board Makefile target availability;
- host-tool availability for simulation, synthesis, packing, and loading;
- optional NEORV32 checkout readiness;
- pre-board validation commands;
- first bring-up command sequence.

This is the last lightweight check before wiring the wrapper into an actual
NEORV32 Gowin/Tang Nano project.
