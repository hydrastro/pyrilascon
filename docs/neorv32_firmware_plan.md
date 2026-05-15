# NEORV32 ASCON firmware plan

The standalone Tang Nano 9K targets do not require C firmware. Firmware becomes
necessary when the ASCON core is wrapped as a NEORV32 CFS/MMIO peripheral.

This repository currently provides a firmware driver scaffold for the intended
register interface. The scaffold intentionally includes all requested modes:

- AEAD128
- AEAD128a
- AEAD128pq
- HASH
- HASHA
- XOF
- XOFA
- CXOF128

Only the NIST AEAD128/HASH/XOF/CXOF software model is currently KAT-backed in the
Python golden model. Legacy/extra modes remain API-visible placeholders until the
corresponding RTL and KATs are added.

## Recommended bring-up order

1. Standalone `ascon_aead128_full_slow` FPGA KAT target.
2. Minimal NEORV32 system with an ASCON CFS/MMIO wrapper.
3. Firmware writes key/nonce/length/data to the MMIO peripheral.
4. Firmware compares hardware output against known-answer vectors.
5. Firmware benchmarks hardware cycles against software cycles.


## Frozen accelerator ABI

The NEORV32 CFS wrapper must implement the frozen ASCON accelerator register map documented in `docs/ascon_accel_register_map.md`. The same firmware driver is intended to work with the slow Tang Nano 9K core and later higher-throughput FPGA cores, provided the wrapper preserves the ABI and reports supported algorithms/features through `ASCON_REG_CAPABILITIES`.
