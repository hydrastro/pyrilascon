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
| `ascon_accel_axis_mmio_transport.h/.c` | CPU-driven MMIO bridge transport for 128-bit AXI-stream bring-up |
| `ascon_accel.c` | High-level AEAD/hash/XOF API composition |
| `ascon_accel_benchmark.h/.c` | Cycle-count wrappers and benchmark result helpers |
| `main_demo.c` | Host-buildable API smoke example |

## Data-plane rule

The public API remains stable. The selected data plane controls how payload bytes move:

- `ASCON_ACCEL_DATA_PLANE_MMIO_WORD`: CPU writes/reads `DATA_IN` and `DATA_OUT` registers. This is the NEORV32/CFS baseline and the default.
- `ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL`: control is still CSR/MMIO, but payload movement is provided by an installed `ascon_accel_axis_transport_t` callback table. Platform-specific code may implement these callbacks using DMA, a stream FIFO, or a vendor-specific streaming interface.

Firmware must check `ASCON_REG_ABI_VERSION` and `ASCON_REG_CAPABILITIES` before using optional modes. Faster FPGA cores should preserve the ABI and only change latency/throughput/capability bits.


## AXI Stream transport callbacks

The driver does not hardcode a specific DMA controller. High-throughput systems install callbacks with `ascon_accel_set_axis_transport()`, then select `ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL`. See `docs/firmware_driver_architecture.md` for the software contract.

## Host-side AXI Stream mock

For driver-level tests that do not have a real AXI Stream or DMA engine, use:

```text
ascon_accel_axis_mock_transport.h
ascon_accel_axis_mock_transport.c
```

The mock records AD/text/customization streams separately and provides a preloadable RX buffer. See `docs/axis_transport_mocking.md`.



## CPU-driven AXI Stream MMIO bridge transport

For NEORV32/Tang Nano bring-up before DMA exists, platform code can use:

```text
ascon_accel_axis_mmio_transport.h
ascon_accel_axis_mmio_transport.c
```

This transport maps the callback-based AXI Stream data plane onto a small
platform-specific MMIO stream bridge at `ASCON_ACCEL_AXIS_MMIO_BASE_ADDR`. The
frozen ASCON CSR base remains separate from the stream bridge base. The transport
chunks payloads into 128-bit beats, emits contiguous `tkeep` masks, preserves
`AD`/`TEXT`/`CUSTOM` stream kinds through `tuser`, and requires exact receive
length agreement. See `docs/firmware_axis_mmio_transport.md`.

## Benchmark helpers

`ascon_accel_benchmark.h` wraps the normal AEAD API and records accelerator cycle-counter values before and after the operation. The helper reports elapsed cycles and milli-cycles-per-byte so the same firmware can compare slow MMIO, AXI Stream, DMA, and future multi-context cores through one result structure.

The benchmark helper measures accelerator-visible cycles. A NEORV32 demo should also measure the software reference using the CPU cycle counter, then report both values. The acceptance rule for hardware acceleration is simple: the accelerator configuration must beat the NEORV32 software implementation for every mode it claims through `ASCON_REG_CAPABILITIES`.

## Stream-native SoC sequencing

For `ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL`, the driver asserts
`CONTROL.START` before invoking the transport `send()` callbacks. This matches
the stream-native SoC top, which accepts AD/text beats only after start. The
default MMIO word data plane keeps the legacy order: payload is written to
`DATA_IN` before `CONTROL.START`.

Buffered decrypt tag failures are reported as `ASCON_ACCEL_ERR_TAG_INVALID` by
translating `ASCON_ERROR_TAG_INVALID` from the hardware error-code register.

## AXI-MMIO bridge RTL counterpart

`ascon_accel_axis_mmio_transport.c` matches the RTL register block implemented by
`rtl/common/ascon_axis_mmio_bridge.v`.  For an integrated stream-native AEAD128
bring-up target, use `rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v`.
