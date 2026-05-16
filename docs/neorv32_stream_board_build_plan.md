# NEORV32 stream board dry-run build plan

The Tang Nano 9K / NEORV32 stream target now has a dry-run build-plan tool:

```sh
make neorv32-stream-board-build-plan
```

The target first ensures the deterministic board package exists, then writes:

```text
build/neorv32_stream_axis_mmio/build_plan.json
build/neorv32_stream_axis_mmio/build_plan.md
```

The plan does **not** synthesize, place, route, pack, or program hardware. It is
an integration sanity check for the board handoff package before running the real
FPGA flow.

## What the plan checks

The dry-run plan validates:

- generated package metadata;
- manifest and preflight JSON files;
- CSR and AXI-MMIO base addresses;
- presence of the stream CFS wrapper and accelerator system source;
- mixed Verilog/VHDL source split;
- existence of every RTL source referenced by the package;
- generated firmware header and make fragment;
- stream firmware mode `USE_CFS_AXIS_MMIO=1`.

It also records optional host-tool availability for `iverilog`, `vvp`, Gowin
open-source flow tools, and `openFPGALoader`. Missing optional FPGA tools are
reported in the JSON/Markdown plan but do not fail the dry-run.

## Board-local command

From the board scaffold directory, run:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio build-plan
```

## Intended sequence

A clean pre-board handoff now looks like:

```sh
make neorv32-stream-board-manifest
make neorv32-stream-board-preflight
make neorv32-stream-board-package
make neorv32-stream-board-build-plan
```

After that, build the NEORV32 benchmark firmware with:

```sh
make -C firmware/neorv32_ascon_benchmark \
  NEORV32_HOME=/path/to/neorv32 \
  USE_CFS_AXIS_MMIO=1 \
  clean_all exe
```

Then integrate `rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd` as the
NEORV32 CFS implementation, synthesize the board project, capture UART output,
and run:

```sh
make neorv32-stream-uart-report LOG=/path/to/uart.log
```
