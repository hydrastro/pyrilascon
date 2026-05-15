# AXI Stream Data Plane

The accelerator ABI keeps the frozen 32-bit MMIO/CSR register map for control,
status, key, nonce, lengths, tags, capabilities, cycle counters, and errors.
Bulk payload movement can use an AXI4-Stream-style data plane.

This is the intended FPGA architecture:

```text
control/status/key/nonce/tag/lengths -> MMIO/CSR
AD/plaintext/ciphertext bytes        -> AXI Stream
ciphertext/plaintext bytes           -> AXI Stream
```

The MMIO `DATA_IN` and `DATA_OUT` registers remain supported as a compatibility
path. They are useful for NEORV32 CFS-only designs and small tests. High-throughput
FPGA designs should use the stream data plane.

## Input stream

The first AXI stream wrapper is `rtl/common/ascon_accel_axis_aead128_top.v`.
It uses 32-bit stream words because the current backend is still the bounded
slow backend. Future high-throughput wrappers may widen this to 64, 128, or more
bits while preserving the same segment semantics.

```verilog
s_axis_tdata  [31:0]
s_axis_tkeep  [3:0]
s_axis_tvalid
s_axis_tready
s_axis_tlast
s_axis_tuser  [3:0]
```

`tkeep[0]` corresponds to `tdata[7:0]`. Data is little-endian within each word.

`tuser` identifies the stream segment:

| Value | Segment |
|---:|---|
| `4'h1` | associated data |
| `4'h2` | plaintext/ciphertext text stream |
| `4'h3` | CXOF customization stream |

For the current AEAD128 backend, only AD and TEXT are accepted.

## Output stream

```verilog
m_axis_tdata  [31:0]
m_axis_tkeep  [3:0]
m_axis_tvalid
m_axis_tready
m_axis_tlast
m_axis_tuser  [3:0]
```

Output `tuser` is currently TEXT. During decryption, output stream data must not
become valid until tag verification succeeds. This preserves the mandatory
buffer-until-verify policy.

## Capability bit

Hardware that implements the stream data plane sets:

```text
ASCON_CAP_AXI_STREAM_DATA
```

Software should still probe `CAPABILITIES`. A CPU-only CFS integration can use
the MMIO data registers, while an FPGA wrapper with DMA or stream fabric can use
AXI Stream for the payload. The portable firmware driver exposes this through
`ascon_accel_axis_transport_t` callbacks rather than hardcoding a specific DMA IP.
If `ASCON_CAP_AXI_STREAM_DATA` is missing, stream transport is rejected. If the
capability is present but callbacks are not installed, the driver returns
`ASCON_ACCEL_ERR_TRANSPORT`.

## NEORV32 note

The NEORV32 CFS itself is a memory-mapped custom-function interface, not an AXI
Stream master. Therefore the first NEORV32 integration can still use the MMIO data
registers. A later FPGA SoC can add a CFS control block plus a stream/DMA feeder,
using the same frozen control ABI and the AXI Stream data plane.


## Host-side transaction oracle

`ascon_hwmodel/aead_stream.py` is the executable reference for the intended
unbounded AEAD128 stream backend. It is deliberately byte-oriented and mirrors
the frozen ABI split: key, nonce, lengths, mode, and tag remain on the control
plane; AD and TEXT are packed into stream beats.

The oracle enforces the FPGA stream rules before running the scalar AEAD model:

- `tkeep`/bytemask must be contiguous from byte 0;
- non-final beats must be completely full;
- every non-empty stream must end with exactly one `last` beat;
- the stream length must match the CSR length register;
- decryption suppresses plaintext output unless tag verification succeeds.

The old bounded RTL backend remains in place. The next RTL milestone is to make
`ascon_aead128_stream_backend` match this oracle for arbitrary AD and TEXT
lengths, then replace the bounded backend inside the AXI wrappers.
