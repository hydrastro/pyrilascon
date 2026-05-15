# ASCON Accelerator Register Map

ABI version: `1`

This document freezes the software-visible MMIO ABI for the ASCON accelerator. Future slow, fast, single-core, multi-core, Gowin, or Xilinx implementations should preserve this register map. Hardware may expose fewer algorithms by clearing capability bits.

All registers are 32-bit little-endian words at byte offsets from the accelerator base address. Multi-word keys, nonces, tags, and data streams use little-endian byte order within each 32-bit word.

## Register offsets

| Offset | Name | Access | Description |
|---:|---|---|---|
| `0x00` | `ASCON_REG_CONTROL` | RW | Command register. Write START to launch an operation; write CLEAR to reset/clear status. |
| `0x04` | `ASCON_REG_STATUS` | RO | Status register. |
| `0x08` | `ASCON_REG_MODE` | RW | Selected algorithm/mode identifier. |
| `0x0C` | `ASCON_REG_CAPABILITIES` | RO | Hardware feature bitmap. |
| `0x10` | `ASCON_REG_AD_LEN` | RW | Associated-data length in bytes. |
| `0x14` | `ASCON_REG_TEXT_LEN` | RW | Plaintext/ciphertext/message length in bytes. |
| `0x18` | `ASCON_REG_OUT_LEN` | RW | Requested output length in bytes for hash/XOF/CXOF modes. |
| `0x1C` | `ASCON_REG_CUSTOM_LEN` | RW | Customization-string length in bytes for CXOF-like modes. |
| `0x20` | `ASCON_REG_KEY0` | RW | Key word 0, little-endian bytes 0..3. |
| `0x24` | `ASCON_REG_KEY1` | RW | Key word 1, little-endian bytes 4..7. |
| `0x28` | `ASCON_REG_KEY2` | RW | Key word 2, little-endian bytes 8..11. |
| `0x2C` | `ASCON_REG_KEY3` | RW | Key word 3, little-endian bytes 12..15. |
| `0x30` | `ASCON_REG_NONCE0` | RW | Nonce word 0, little-endian bytes 0..3. |
| `0x34` | `ASCON_REG_NONCE1` | RW | Nonce word 1, little-endian bytes 4..7. |
| `0x38` | `ASCON_REG_NONCE2` | RW | Nonce word 2, little-endian bytes 8..11. |
| `0x3C` | `ASCON_REG_NONCE3` | RW | Nonce word 3, little-endian bytes 12..15. |
| `0x40` | `ASCON_REG_DATA_IN` | WO | Input data word, little-endian byte order. |
| `0x44` | `ASCON_REG_DATA_IN_CTRL` | WO | Input stream control: valid, last, kind, and byte keep mask. |
| `0x48` | `ASCON_REG_DATA_OUT` | RO | Output data word, little-endian byte order. |
| `0x4C` | `ASCON_REG_DATA_OUT_CTRL` | RO | Output stream control: valid, last, and byte keep mask. |
| `0x60` | `ASCON_REG_TAG0` | RW | Tag word 0. Encryption reads generated tag; decryption writes expected tag. |
| `0x64` | `ASCON_REG_TAG1` | RW | Tag word 1. Encryption reads generated tag; decryption writes expected tag. |
| `0x68` | `ASCON_REG_TAG2` | RW | Tag word 2. Encryption reads generated tag; decryption writes expected tag. |
| `0x6C` | `ASCON_REG_TAG3` | RW | Tag word 3. Encryption reads generated tag; decryption writes expected tag. |
| `0x70` | `ASCON_REG_CYCLE_COUNT_LO` | RO | Low 32 bits of implementation-defined cycle counter for benchmarking. |
| `0x74` | `ASCON_REG_CYCLE_COUNT_HI` | RO | High 32 bits of implementation-defined cycle counter for benchmarking. |
| `0x78` | `ASCON_REG_ERROR_CODE` | RO | Implementation-defined error code. |
| `0x7C` | `ASCON_REG_ABI_VERSION` | RO | Register-map ABI version. Current value is 1. |

## CONTROL bits

| Bit | Name | Description |
|---:|---|---|
| 0 | `ASCON_CONTROL_START` | Start the configured operation. |
| 1 | `ASCON_CONTROL_DECRYPT` | AEAD operation is decryption when set, encryption when clear. |
| 2 | `ASCON_CONTROL_HASH` | Operation is hash-like. |
| 3 | `ASCON_CONTROL_XOF` | Operation is XOF-like. |
| 4 | `ASCON_CONTROL_CXOF` | Operation uses customization input. |
| 8 | `ASCON_CONTROL_CLEAR` | Clear/reset the accelerator local state and sticky status. |
| 16 | `ASCON_CONTROL_IRQ_ENABLE` | Enable interrupt generation, if implemented. |

## STATUS bits

| Bit | Name | Description |
|---:|---|---|
| 0 | `ASCON_STATUS_BUSY` | Accelerator is processing. |
| 1 | `ASCON_STATUS_DONE` | Operation completed. |
| 2 | `ASCON_STATUS_TAG_VALID` | Decryption tag verification succeeded. |
| 3 | `ASCON_STATUS_ERROR` | Operation failed. |
| 4 | `ASCON_STATUS_IN_READY` | Input stream can accept a DATA_IN word. |
| 5 | `ASCON_STATUS_OUT_VALID` | DATA_OUT contains a valid output word. |

## Stream control bits

| Bit | Name | Description |
|---:|---|---|
| 0 | `ASCON_DATA_LAST` | This is the final word of this input stream segment. |
| 1 | `ASCON_DATA_VALID` | DATA_IN is valid. |
| 2 | `ASCON_DATA_AD` | Input word belongs to associated data. |
| 3 | `ASCON_DATA_TEXT` | Input word belongs to plaintext/ciphertext/message. |
| 4 | `ASCON_DATA_CUSTOM` | Input word belongs to CXOF customization data. |
| 8..11 | `keep` | Four-bit byte-valid mask. Bit 0 corresponds to byte 0 of the 32-bit word. |

## Mode values

| Value | Name | Description |
|---:|---|---|
| 0 | `ASCON_MODE_AEAD128` | NIST Ascon-AEAD128. |
| 1 | `ASCON_MODE_AEAD128A` | Legacy Ascon-128a placeholder. |
| 2 | `ASCON_MODE_AEAD128PQ` | Legacy/post-quantum-style placeholder. |
| 3 | `ASCON_MODE_HASH` | Ascon-Hash256. |
| 4 | `ASCON_MODE_HASHA` | Hasha placeholder. |
| 5 | `ASCON_MODE_XOF` | Ascon-XOF128. |
| 6 | `ASCON_MODE_XOFA` | XOFa placeholder. |
| 7 | `ASCON_MODE_CXOF128` | Ascon-CXOF128. |

## Capability bits

| Bit | Name | Description |
|---:|---|---|
| 0 | `ASCON_CAP_AEAD128` | Ascon-AEAD128 is implemented. |
| 1 | `ASCON_CAP_AEAD128A` | Ascon-128a-compatible mode is implemented. |
| 2 | `ASCON_CAP_AEAD128PQ` | Ascon-128pq-compatible mode is implemented. |
| 3 | `ASCON_CAP_HASH` | Hash mode is implemented. |
| 4 | `ASCON_CAP_HASHA` | Hasha mode is implemented. |
| 5 | `ASCON_CAP_XOF` | XOF mode is implemented. |
| 6 | `ASCON_CAP_XOFA` | XOFa mode is implemented. |
| 7 | `ASCON_CAP_CXOF128` | CXOF128 mode is implemented. |
| 16 | `ASCON_CAP_DECRYPT_BUFFERED` | Plaintext release is buffered until tag verification succeeds. |
| 17 | `ASCON_CAP_CONSTTIME_TAG_COMPARE` | Tag comparison is intended to be constant-time. |
| 18 | `ASCON_CAP_RAND_COUNTER_HARDENING` | Control counters include randomization/hardening, if randomness is supplied. |
| 19 | `ASCON_CAP_FAULT_DETECTION` | Fault-detection mechanism is implemented. |
| 20 | `ASCON_CAP_STREAMING_BYTEMASK` | Input stream supports final-byte keep mask. |
| 21 | `ASCON_CAP_CYCLE_COUNTER` | Cycle counter registers are implemented. |

## Error codes

| Value | Name | Description |
|---:|---|---|
| 0 | `ASCON_ERROR_NONE` | No error. |
| 1 | `ASCON_ERROR_UNSUPPORTED_MODE` | Selected mode is not implemented by this hardware instance. |
| 2 | `ASCON_ERROR_BAD_LENGTH` | Unsupported or inconsistent length fields. |
| 3 | `ASCON_ERROR_STREAM_PROTOCOL` | Input/output stream protocol violation. |
| 4 | `ASCON_ERROR_TAG_INVALID` | AEAD decryption tag mismatch. |
| 5 | `ASCON_ERROR_FAULT_DETECTED` | Fault-detection logic detected an inconsistency. |

## Decryption plaintext release policy

For AEAD decryption, plaintext must not be made visible through `DATA_OUT` until tag verification has succeeded. If verification fails, the implementation must clear or invalidate any internal plaintext buffer and set `ERROR` with `ERROR_CODE = ASCON_ERROR_TAG_INVALID`.

## Compatibility rule

Firmware must probe `CAPABILITIES` and `ABI_VERSION` before using optional algorithms or features. A faster accelerator must preserve the observable behavior of this ABI; performance changes should appear only as shorter `BUSY` duration and different cycle-counter values.
