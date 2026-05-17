# NEORV32 CFS Integration

This repository integrates the ASCON accelerator through the NEORV32 Custom
Functions Subsystem (CFS). The CFS is the correct NEORV32 extension point for a
memory-mapped, processor-internal co-processor: software accesses it through
ordinary load/store instructions, while the custom hardware remains independent
from the CPU pipeline.

## Software-visible address map

The accelerator uses the frozen pyrilascon MMIO ABI. NEORV32 maps the CFS to:

```text
ASCON_ACCEL_BASE_ADDR = 0xffeb0000
```

Therefore accelerator register offset `0x00` is available at absolute address
`0xffeb0000`, offset `0x04` at `0xffeb0004`, and so on.

The register offsets themselves are generated from:

```text
ascon_arch/register_map.py
```

and emitted to:

```text
firmware/ascon_accel/ascon_accel_regs.h
rtl/common/ascon_accel_regs.vh
```

## Hardware files

The first NEORV32-facing integration step is:

```text
rtl/neorv32/neorv32_cfs_ascon.vhd
```

This file deliberately defines the canonical NEORV32 entity name:

```vhdl
entity neorv32_cfs is
```

so it is a drop-in replacement for the stock NEORV32 CFS template.

The wrapper translates the NEORV32 internal bus request record into the simple
pyrilascon accelerator bus:

```text
bus_req_i.stb        -> bus_valid_i
bus_req_i.rw         -> bus_write_i
bus_req_i.addr[7:0]  -> bus_addr_i
bus_req_i.data       -> bus_wdata_i
bus_req_i.ben        -> bus_wstrb_i
bus_rsp_o.data       <- bus_rdata_o
bus_rsp_o.ack        <- registered bus_req_i.stb
irq_o                <- accelerator interrupt output
```

The cryptographic backend instantiated by the wrapper is currently:

```text
rtl/common/ascon_accel_mmio_aead128_top.v
```

which connects:

```text
ascon_accel_mmio_regs.v
+
ascon_aead128_mmio_backend.v
```

## Compile integration

Use the helper file list:

```text
rtl/neorv32/ascon_cfs_file_list.f
```

When building a NEORV32 system:

1. Compile the normal NEORV32 `rtl/core` files into the `neorv32` VHDL library.
2. Exclude or disable the stock `rtl/core/neorv32_cfs.vhd`.
3. Compile `rtl/neorv32/neorv32_cfs_ascon.vhd` into the same `neorv32` library.
4. Add the Verilog files listed in `rtl/neorv32/ascon_cfs_file_list.f`.
5. Enable the CFS in the NEORV32 top-level generics.

Mixed-language support is required because the wrapper is VHDL and the current
accelerator backend is Verilog. Commercial FPGA tools usually support this. For
the open-source Gowin flow, this may require a GHDL/Yosys mixed-language setup;
otherwise use the standalone Verilog board targets first.

## Firmware

The firmware driver is in:

```text
firmware/ascon_accel/
```

The NEORV32 demo scaffold is in:

```text
firmware/neorv32_ascon_demo/
```

The driver expects the frozen CFS base address by default:

```c
#define ASCON_ACCEL_BASE_ADDR 0xFFEB0000u
```

The first backend advertises only these major capabilities:

```text
AEAD128
DECRYPT_BUFFERED
CONSTTIME_TAG_COMPARE
CYCLE_COUNTER
```

Other firmware-visible modes remain part of the ABI, but this backend returns
unsupported-mode behavior for them until additional hardware cores are added.

## Current limitation

This is the first CFS integration step. It provides the VHDL CFS replacement and
connects the real AEAD128 MMIO backend, but it does not yet include a full
Tang-Nano-9K NEORV32 SoC build script. The next milestone is a board-level
NEORV32 top, firmware image generation, and UART demo.

## AXI Stream data-plane direction

The NEORV32 CFS integration is still useful as a simple CPU-controlled baseline,
but it is not the final high-throughput FPGA data path. The project now separates
control and data movement:

```text
CFS/MMIO/CSR: control, status, key, nonce, lengths, tags, capabilities
AXI Stream:  associated data, plaintext, ciphertext, and future hash/XOF data
```

The current CFS wrapper can use the compatibility `DATA_IN`/`DATA_OUT` registers.
Future FPGA wrappers should instantiate `ascon_accel_axis_aead128_top` or a wider
successor and feed its stream ports from a DMA/stream fabric while keeping the
same frozen control ABI.
