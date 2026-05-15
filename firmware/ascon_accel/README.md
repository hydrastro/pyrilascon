# ASCON accelerator firmware driver

This directory contains the portable C driver for the pyrilascon accelerator ABI.
The driver is intentionally split into a stable public API and separate control/data-plane layers so the same firmware can target slow MMIO cores, AXI Stream/DMA-backed FPGA cores, and future NEORV32/Xilinx wrappers.

## Files

| File | Purpose |
| --- | --- |
| `ascon_accel.h` | Public API, mode enums, request structures, data-plane selection |
| `ascon_accel_regs.h` | Generated register/capability constants from `ascon_arch/register_map.py` |
| `ascon_accel_internal.h` | Private helper declarations shared by the driver translation units |
| `ascon_accel_control.c` | Register access, reset, cycle counter, key/nonce/tag helpers |
| `ascon_accel_caps.c` | ABI version, capability probing, mode classification |
| `ascon_accel_mmio_data.c` | Register-based DATA_IN/DATA_OUT transport |
| `ascon_accel_axis_data.c` | External AXI Stream/DMA transport callback dispatch |
| `ascon_accel.c` | High-level AEAD/hash/XOF API composition |
| `main_demo.c` | Host-buildable API smoke example |

## Data-plane rule

The public API remains stable. The selected data plane controls how payload bytes move:

- `ASCON_ACCEL_DATA_PLANE_MMIO_WORD`: CPU writes/reads `DATA_IN` and `DATA_OUT` registers. This is the NEORV32/CFS baseline and the default.
- `ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL`: control is still CSR/MMIO, but payload movement is provided by an installed `ascon_accel_axis_transport_t` callback table. Platform-specific code may implement these callbacks using DMA, a stream FIFO, or a vendor-specific streaming interface.

Firmware must check `ASCON_REG_ABI_VERSION` and `ASCON_REG_CAPABILITIES` before using optional modes. Faster FPGA cores should preserve the ABI and only change latency/throughput/capability bits.


## AXI Stream transport callbacks

The driver does not hardcode a specific DMA controller. High-throughput systems install callbacks with `ascon_accel_set_axis_transport()`, then select `ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL`. See `docs/firmware_driver_architecture.md` for the software contract.
