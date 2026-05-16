# Firmware CPU-driven AXI-stream MMIO transport

This slice adds `ascon_accel_axis_mmio_transport.h/.c`, a portable firmware
transport for bring-up systems where the CPU manually feeds the stream-native
accelerator through a small memory-mapped stream bridge instead of a DMA engine.

The important separation remains:

```text
ASCON_ACCEL_BASE_ADDR
  frozen accelerator control/status CSR map

ASCON_ACCEL_AXIS_MMIO_BASE_ADDR
  platform-specific MMIO bridge connected to s_axis/m_axis
```

The high-level driver still uses the normal `ascon_accel_axis_transport_t`
callback table. Platform code initializes the bridge transport, installs it with
`ascon_accel_set_axis_transport()`, and selects
`ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL`.

## Bridge register contract

The bridge is intentionally tiny and 128-bit wide. TX registers carry one stream
beat into the accelerator, and RX registers expose one stream beat produced by
the accelerator.

```text
TX_DATA0..TX_DATA3   128-bit little-endian beat payload
TX_KEEP              16-bit contiguous low-byte keep mask
TX_USER              stream kind: AD, TEXT, or CUSTOM
TX_CTRL              VALID and LAST
STATUS               TX_READY, RX_VALID, RX_LAST, ERROR
RX_DATA0..RX_DATA3   128-bit little-endian output beat payload
RX_KEEP              16-bit contiguous low-byte keep mask
RX_USER              output stream kind
RX_CTRL              POP acknowledgement
```

The firmware transport chunks arbitrary byte strings into 16-byte beats. It does
not emit dummy beats for zero-length streams. For receive, it requires contiguous
low-byte `RX_KEEP`, exact byte count agreement with the caller's requested
length, and `RX_LAST` on the final beat.

## Why this exists before DMA

The stream-native SoC top already exposes a true AXI-stream data plane. A real
high-throughput system should eventually use DMA or a vendor stream frontend.
However, a CPU-driven bridge is useful for NEORV32/Tang Nano bring-up because it
lets firmware exercise the exact stream backend and authenticated-decrypt policy
without adding a DMA controller first.

The expected bring-up stack is now:

```text
NEORV32 firmware
  -> frozen ASCON CSR block
  -> ascon_accel_axis_mmio_transport callbacks
  -> small MMIO-to-AXI-stream bridge
  -> ascon_accel_stream_aead128_top
```

Later DMA integration can replace only the transport callbacks; the high-level
AEAD API and stream backend do not change.
