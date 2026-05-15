# NEORV32 RTL integration notes

The NEORV32 target is not a complete SoC in this repository yet. The current
integration point is the frozen ASCON MMIO register bank in `rtl/common/`.

## Current files

- `rtl/common/ascon_accel_regs.vh`
- `rtl/common/ascon_accel_mmio_regs.v`
- `rtl/common/ascon_accel_core_stub.v`
- `rtl/common/ascon_accel_mmio_stub_top.v`

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
