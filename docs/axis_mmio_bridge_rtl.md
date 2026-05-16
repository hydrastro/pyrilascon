# AXI Stream MMIO Bridge RTL

`ascon_axis_mmio_bridge` is the hardware counterpart to
`ascon_accel_axis_mmio_transport.c`. It is intended for NEORV32 and early board
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
0x1c        STATUS: bit0 TX_READY, bit1 RX_VALID, bit2 RX_LAST,
                    bits[15:8] RX_LEVEL, bit31 ERROR
0x20..0x2c  RX_DATA0..3
0x30        RX_KEEP
0x34        RX_USER
0x38        RX_CTRL: bit0 POP
```

The CPU writes TX data, keep, user, and finally `TX_CTRL.VALID`. That commits
one beat into a single-beat TX holding register. `STATUS.TX_READY` is high only
when this holding register is empty.

The RX FIFO side is FIFO-backed. When the accelerator produces an output beat, the
bridge enqueues it and raises `STATUS.RX_VALID`. Firmware reads the oldest
queued beat through `RX_*` and then writes `RX_CTRL.POP` to release that beat.
`STATUS.RX_LEVEL` exposes the current queued-beat count as a debug/bring-up aid;
the existing firmware transport does not need it for correctness.

## Why RX uses a FIFO

The CPU-driven transport is not truly full-duplex. Firmware naturally performs:

```text
send AD/text beats
then read ciphertext/plaintext beats
```

A pure one-beat RX holding register can stall the stream backend if the backend
returns one ciphertext beat while firmware is still sending later plaintext
beats. The FIFO-backed RX side gives early NEORV32/Tang Nano bring-up enough
elasticity for small multi-beat messages before a DMA frontend exists.

TX remains one beat deep because firmware already waits for `STATUS.TX_READY`
before writing `TX_CTRL.VALID` for the next input beat.

## Integrated system wrapper

`ascon_accel_stream_aead128_axis_mmio_system` instantiates:

```text
ascon_axis_mmio_bridge
    +
ascon_accel_stream_aead128_top
```

This wrapper is the most convenient RTL target for initial NEORV32/Tang Nano
stream-native bring-up. It preserves the frozen accelerator CSR window while
adding the second MMIO window consumed by the firmware AXI-MMIO transport.

The wrapper forwards `RX_FIFO_DEPTH` into the bridge so small FPGA builds can
choose the amount of CPU-side output elasticity.

## Limitations

This bridge is for correctness and bring-up, not peak throughput. It moves one
128-bit beat per CPU polling/commit cycle. The FIFO prevents the most immediate
CPU-driven multi-beat deadlock, but high-throughput systems should still replace
it with a DMA-fed AXI-stream frontend while keeping the same
`ascon_accel_stream_aead128_top` backend.
