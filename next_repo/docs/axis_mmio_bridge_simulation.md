# AXI-stream MMIO bridge behavioral simulation

`tools/run_axis_mmio_bridge_vector.py` generates a small Icarus Verilog testbench for
`rtl/common/ascon_axis_mmio_bridge.v`.

The simulation exercises the bridge independently from the ASCON crypto core:

1. CPU-style MMIO writes populate `TX_DATA*`, `TX_KEEP`, `TX_USER`, and
   `TX_CTRL.VALID/LAST`.
2. The testbench holds `m_axis_tready` low for several cycles to prove the bridge
   holds the committed TX beat stable until an AXI-stream handshake occurs.
3. The testbench injects one RX AXI-stream beat.
4. CPU-style MMIO reads fetch `RX_DATA*`, `RX_KEEP`, `RX_USER`, and `STATUS`.
5. A write to `RX_CTRL.POP` releases the RX holding register.

Run the default vector with:

```bash
make axis-mmio-bridge-sim
```

Or directly:

```bash
PYTHONPATH=. python tools/run_axis_mmio_bridge_vector.py --json
```

Use `--dry-run` to inspect the generated testbench without requiring
`iverilog`/`vvp`.

This test is a pre-board smoke test for the CPU-driven stream path:

```text
NEORV32 firmware
  -> ascon_accel_axis_mmio_transport.c
  -> ascon_axis_mmio_bridge.v
  -> AXI Stream
  -> ascon_accel_stream_aead128_top
```
