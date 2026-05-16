# NEORV32 RTL integration notes

The NEORV32 target is not a complete SoC in this repository yet. The current
integration point is the frozen ASCON MMIO register bank in `rtl/common/`.

## Current files

MMIO baseline CFS wrapper:

- `rtl/neorv32/neorv32_cfs_ascon.vhd`
- `rtl/neorv32/ascon_cfs_file_list.f`

Stream-native CFS wrapper:

- `rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd`
- `rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f`

Common RTL blocks:

- `rtl/common/ascon_accel_regs.vh`
- `rtl/common/ascon_accel_mmio_regs.v`
- `rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v`
- `rtl/common/ascon_axis_mmio_bridge.v`

## How to connect to NEORV32 CFS

Use the CFS register index as a byte-addressed offset into the ASCON ABI:

```text
CFS REG[0]  -> 0x00 CONTROL
CFS REG[1]  -> 0x04 STATUS
CFS REG[2]  -> 0x08 MODE
...
CFS REG[31] -> 0x7C ABI_VERSION
```

The future CFS wrapper should convert CFS read/write strobes into:

```verilog
bus_valid_i
bus_write_i
bus_addr_i
bus_wdata_i
bus_wstrb_i
bus_rdata_o
bus_ready_o
```

The current `ascon_accel_core_stub` is not cryptographic. Replace it with the
real AEAD128 core once the bus wrapper is verified.

## Stream-native CFS wrapper

The preferred board-facing stream target is:

```text
rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd
```

It maps one NEORV32 CFS region into two local windows:

```text
0x000..0x0ff -> frozen ASCON CSR/MMIO ABI
0x100..0x1ff -> CPU-driven AXI-stream MMIO bridge
```

Build the firmware benchmark for this wrapper with:

```sh
make NEORV32_HOME=/path/to/neorv32 USE_CFS_AXIS_MMIO=1 clean_all exe
```

This defines `ASCON_ACCEL_AXIS_MMIO_BASE_ADDR=0xFFEB0100u` while preserving
`ASCON_ACCEL_BASE_ADDR=0xFFEB0000u`.
