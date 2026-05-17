# Firmware Driver Architecture

The firmware driver is intentionally split into a stable public API and pluggable
transport layers. This keeps one software API usable across slow NEORV32/CFS
implementations, high-throughput AXI Stream FPGA implementations, and future DMA
or vendor-specific wrappers.

## Layers

```text
application / benchmark
        |
        v
ascon_accel_encrypt/decrypt/hash_or_xof
        |
        +--> control plane: CONTROL, STATUS, MODE, CAPABILITIES, lengths, key, nonce, tag
        |
        +--> data plane selected per device instance
              - MMIO DATA_IN/DATA_OUT registers
              - external AXI Stream/DMA transport callback
```

The public entry points live in `ascon_accel.h`. The implementation is split into:

| File | Role |
| --- | --- |
| `ascon_accel.c` | high-level operation sequencing |
| `ascon_accel_control.c` | CSR/MMIO access, reset, cycle counter, key/nonce/tag helpers |
| `ascon_accel_caps.c` | ABI and capability probing |
| `ascon_accel_mmio_data.c` | 32-bit register data transport |
| `ascon_accel_axis_data.c` | external AXI Stream/DMA callback transport |

## Data-plane selection

A device starts in the MMIO data-plane mode:

```c
ascon_accel_t dev;
ascon_accel_init(&dev, ASCON_ACCEL_BASE_ADDR, 1000000u);
```

For high-throughput FPGA systems, software can select the external stream data
plane and install platform-specific callbacks:

```c
static ascon_accel_status_t axis_send(
    void *ctx,
    const uint8_t *data,
    size_t len,
    ascon_accel_stream_kind_t kind) {
  /* platform-specific DMA or AXI Stream enqueue */
  return ASCON_ACCEL_OK;
}

static ascon_accel_status_t axis_recv(void *ctx, uint8_t *data, size_t len) {
  /* platform-specific DMA or AXI Stream dequeue */
  return ASCON_ACCEL_OK;
}

ascon_accel_axis_transport_t transport = {
  .ctx = platform_dma_context,
  .send = axis_send,
  .recv = axis_recv,
};

ascon_accel_set_axis_transport(&dev, &transport);
ascon_accel_set_data_plane(&dev, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL);
```

The high-level crypto API does not change. Only the data mover changes.


## Operation sequencing

The control/data-plane ordering intentionally differs by backend:

- MMIO word data plane: firmware writes all payload words into `DATA_IN` first,
  then asserts `CONTROL.START`. This preserves compatibility with the older
  register-buffered backend.
- External AXI Stream data plane: firmware programs mode, lengths, key/nonce,
  and expected tag, asserts `CONTROL.START`, then invokes the installed stream
  `send()` callbacks. Stream-native RTL such as
  `ascon_accel_stream_aead128_top` only raises `s_axis_tready` after start.

Platform transports used with `ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL` must
therefore be able to move output concurrently with input or provide enough RX
buffering for streaming encryption, because ciphertext can be produced while
plaintext beats are still being sent. Buffered decrypt releases plaintext only
after authentication succeeds.

Hardware error codes are translated back into public firmware statuses. In
particular, `ASCON_ERROR_TAG_INVALID` maps to
`ASCON_ACCEL_ERR_TAG_INVALID`, so authenticated decrypt failures are not reported
as generic hardware faults.

## Capability checks

A hardware instance that supports the stream data plane must set:

```text
ASCON_CAP_AXI_STREAM_DATA
```

The driver checks this bit before using the external stream path. If the bit is
absent, AXI Stream operations return `ASCON_ACCEL_ERR_UNSUPPORTED_MODE`. If the
bit is present but no callback transport is installed, they return
`ASCON_ACCEL_ERR_TRANSPORT`.

## Portability rule

Firmware portability depends on the frozen ABI, not on the internal hardware
microarchitecture. The same high-level driver can target:

```text
1 round/cycle backend
4 rounds/cycle backend
8 rounds/cycle backend
fully pipelined backend
N identical AEAD cores
M pipelines × N contexts
```

provided the generated hardware preserves the register ABI, reports capabilities
honestly, and implements the selected data-plane contract.
