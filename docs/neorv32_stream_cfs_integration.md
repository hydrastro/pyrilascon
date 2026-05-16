# NEORV32 Stream-Native CFS Integration

This page describes the board-facing CFS wrapper for the stream-native
Ascon-AEAD128 backend.  It is the bridge between the validated RTL simulation
stack and a NEORV32 system image.

## Wrapper

Use this file as the NEORV32 CFS replacement:

```text
rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd
```

Like the earlier MMIO-only wrapper, it deliberately defines the canonical
NEORV32 entity:

```vhdl
entity neorv32_cfs is
```

Compile either the legacy MMIO wrapper or this stream-native wrapper, never both.

## CFS-relative memory map

The wrapper instantiates:

```text
ascon_accel_stream_aead128_axis_mmio_system
```

and splits one CFS address region into two local windows:

```text
CFS base + 0x000..0x0ff -> frozen ASCON CSR/MMIO ABI
CFS base + 0x100..0x1ff -> CPU-driven AXI-stream MMIO bridge
```

For the default NEORV32 CFS base this means:

```text
ASCON_ACCEL_BASE_ADDR           = 0xffeb0000
ASCON_ACCEL_AXIS_MMIO_BASE_ADDR = 0xffeb0100
```

The VHDL wrapper uses `bus_req_i.addr(8)` as the window select and forwards
`bus_req_i.addr(7 downto 0)` as the register offset inside the selected local
window.

## Firmware build

For this wrapper, build the benchmark with:

```sh
make NEORV32_HOME=/path/to/neorv32 USE_CFS_AXIS_MMIO=1 clean_all exe
```

`USE_CFS_AXIS_MMIO=1` implies `USE_AXIS_MMIO=1` and defines:

```text
ASCON_ACCEL_AXIS_MMIO_BASE_ADDR=0xFFEB0100u
```

The benchmark still uses the same driver API and the same frozen accelerator
control ABI.  Only the AXI-stream transport base changes from an external bridge
window to the local CFS `+0x100` bridge window.

## RTL file list

Use the helper file list:

```text
rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f
```

It includes the stream encrypt/decrypt RTL, the unified stream backend, the
AXI-MMIO bridge with RX FIFO, the integrated stream system wrapper, and the VHDL
CFS wrapper.

## Debug conduit

The wrapper does not require NEORV32 conduit signals for normal operation, but
it exposes a small debug vector on `cfs_out_o`:

```text
bit 0 -> accelerator IRQ
bit 1 -> AXI bridge error
bit 2 -> selected AXI bridge window
bit 3 -> selected-window ready
```

This is intended only for board bring-up and optional LED/debug pin wiring.

## Status

This is a board-facing integration scaffold.  The RTL blocks below it already
have Python and Icarus-Verilog simulation coverage, including multi-beat
AXI-MMIO system vectors that exercise the bridge RX FIFO.  The remaining work is
project/board integration: compile the mixed-language CFS replacement into a
NEORV32 SoC build, load the firmware, and capture the UART benchmark output.
