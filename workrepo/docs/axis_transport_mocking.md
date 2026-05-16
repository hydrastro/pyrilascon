# AXI Stream Transport Mocking

The accelerator firmware has a stable public API, but high-throughput FPGA designs move payload data through an external AXI Stream or DMA path instead of the 32-bit `DATA_IN`/`DATA_OUT` registers. The file pair below provides a host-side mock transport for testing that API layer before a real board-specific DMA driver exists:

```text
firmware/ascon_accel/ascon_accel_axis_mock_transport.h
firmware/ascon_accel/ascon_accel_axis_mock_transport.c
```

The mock implements `ascon_accel_axis_transport_t` callbacks. It records outgoing associated-data, text, and customization streams in separate buffers, and it provides a preloaded receive buffer for output bytes.

## Typical use

```c
ascon_accel_t dev;
ascon_accel_axis_mock_transport_ctx_t mock;

ascon_accel_init(&dev, base_addr, timeout_cycles);
ascon_accel_axis_mock_init(&mock);

ascon_accel_axis_transport_t transport = ascon_accel_axis_mock_transport(&mock);
ascon_accel_set_axis_transport(&dev, &transport);
ascon_accel_set_data_plane(&dev, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL);
```

A platform-specific implementation should later replace the mock with callbacks backed by an AXI Stream FIFO, AXI DMA, XDMA, PCIe, or another board-level data mover. The high-level firmware API should not change.

## What the mock proves

The mock is not a cryptographic model and does not emulate the RTL accelerator. It proves that:

- the firmware can switch from MMIO payload movement to external stream movement;
- AD, text, and customization streams are separated by `ascon_accel_stream_kind_t`;
- output bytes can be received through the same high-level API shape;
- transport failures are reported as `ASCON_ACCEL_ERR_TRANSPORT`.

This keeps the firmware portable while the RTL backend evolves from slow MMIO, to AXI Stream, to DMA-fed maximum-throughput FPGA architectures.
