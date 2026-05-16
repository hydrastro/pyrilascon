# AXI Stream MMIO Bridge RTL

`ascon_axis_mmio_bridge` is the hardware counterpart to
`ascon_accel_axis_mmio_transport.c`.  It is intended for NEORV32 and early board
bring-up configurations where the CPU manually pushes and pulls AXI-stream beats
through a tiny MMIO register block instead of using DMA.

The bridge is deliberately separate from the frozen ASCON accelerator CSR map.
A system using the stream-native AEAD128 backend therefore exposes two MMIO
windows:

```text
ASCON_ACCEL_BASE_ADDR           -> frozen control/status/key/nonce/tag ABI
ASCON_ACCEL_AXIS_MMIO_BASE_ADDR -> CPU-driven 128-bit stream bridge
```

## Register behavior

The register offsets match `firmware/ascon_accel/ascon_accel_axis_mmio_transport.h`:

```text
0x00..0x0c  TX_DATA0..3
0x10        TX_KEEP
0x14        TX_USER
0x18        TX_CTRL: bit0 VALID, bit1 LAST
0x1c        STATUS: bit0 TX_READY, bit1 RX_VALID, bit2 RX_LAST, bit31 ERROR
0x20..0x2c  RX_DATA0..3
0x30        RX_KEEP
0x34        RX_USER
0x38        RX_CTRL: bit0 POP
```

The CPU writes TX data, keep, user, and finally `TX_CTRL.VALID`.  That commits
one beat into a single-beat TX holding register.  `STATUS.TX_READY` is high only
when this holding register is empty.

The RX side is also one beat deep.  When the accelerator produces an output beat,
the bridge captures it and raises `STATUS.RX_VALID`.  Firmware reads `RX_*` and
then writes `RX_CTRL.POP` to release the slot.

## Integrated system wrapper

`ascon_accel_stream_aead128_axis_mmio_system` instantiates:

```text
ascon_axis_mmio_bridge
    +
ascon_accel_stream_aead128_top
```

This wrapper is the most convenient RTL target for initial NEORV32/Tang Nano
stream-native bring-up.  It preserves the frozen accelerator CSR window while
adding the second MMIO window consumed by the firmware AXI-MMIO transport.

## Limitations

This bridge is for correctness and bring-up, not peak throughput.  It moves one
128-bit beat per CPU polling/commit cycle.  High-throughput systems should
replace it with a DMA-fed AXI-stream frontend while keeping the same
`ascon_accel_stream_aead128_top` backend.
