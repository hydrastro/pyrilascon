# NEORV32 stream Gowin handoff

`tools/prepare_neorv32_stream_gowin_handoff.py` generates an archivable handoff
for the Tang Nano 9K NEORV32 stream-ASCON target.

This is the stage after the board package, build-plan, and session report.  It
collects the exact ASCON CFS integration payload that a Tang Nano / NEORV32
project needs, but it does not pretend that the full mixed-language SoC can be
built with a single generic Yosys command.

## Generate

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio gowin-handoff
```

or from the board directory:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio gowin-handoff
```

The output is:

```text
build/neorv32_stream_axis_mmio/gowin_handoff/
```

## Generated files

```text
README.md
handoff.json
memory_map.json
sources/rtl_sources_verilog.f
sources/rtl_sources_vhdl.f
firmware/neorv32_stream_defines.mk
firmware/ascon_stream_axis_mmio_config.h
scripts/01_preflight.sh
scripts/02_build_firmware.sh
scripts/03_integrate_cfs.sh
scripts/04_program_sram.sh
notes/manual_gowin_integration.md
```

## Purpose

The handoff freezes these facts in one place:

- the firmware-visible ASCON CSR base is `0xFFEB0000`;
- the CPU-driven AXI-stream bridge base is `0xFFEB0100`;
- the firmware build mode is `USE_CFS_AXIS_MMIO=1`;
- the ASCON subsystem Verilog sources are separated from the NEORV32 CFS VHDL
  wrapper;
- board programming remains guarded by an explicit bitstream path.

## Mixed-language note

The target is mixed-language: the ASCON subsystem is Verilog and the NEORV32 CFS
wrapper is VHDL.  Plain Yosys/Gowin flows may need a VHDL-capable frontend, a
vendor flow, or an upstream NEORV32 build integration step.  The generated
handoff records tool availability and source lists, but it does not claim that a
one-command bitstream build exists until the actual board project is wired.

## Typical sequence

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio package
make -C boards/tangnano9k/neorv32_stream_axis_mmio build-plan
make -C boards/tangnano9k/neorv32_stream_axis_mmio gowin-handoff
sh build/neorv32_stream_axis_mmio/gowin_handoff/scripts/01_preflight.sh
sh build/neorv32_stream_axis_mmio/gowin_handoff/scripts/02_build_firmware.sh
```

After the FPGA image is built and programmed, capture UART and parse it with:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio uart-report LOG=/path/to/uart.log
```
