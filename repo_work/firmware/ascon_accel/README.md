# NEORV32 ASCON accelerator firmware scaffold

This directory contains a C driver scaffold for the future NEORV32 CFS/MMIO ASCON
accelerator. It is not used by the standalone Tang Nano 9K KAT targets.

## Supported API modes

The API already names all requested modes:

- `ASCON_ACCEL_MODE_AEAD128`
- `ASCON_ACCEL_MODE_AEAD128A`
- `ASCON_ACCEL_MODE_AEAD128PQ`
- `ASCON_ACCEL_MODE_HASH`
- `ASCON_ACCEL_MODE_HASHA`
- `ASCON_ACCEL_MODE_XOF`
- `ASCON_ACCEL_MODE_XOFA`
- `ASCON_ACCEL_MODE_CXOF128`

Current implementation status:

| Mode | Firmware API | RTL status |
| --- | --- | --- |
| AEAD128 | present | standalone KAT target present; CFS wrapper pending |
| AEAD128a | present | pending |
| AEAD128pq | present | pending |
| HASH | present | pending |
| HASHA | present | pending |
| XOF | present | pending |
| XOFA | present | pending |
| CXOF128 | present | pending |

## Why firmware now if there is no NEORV32 wrapper yet?

The driver fixes the software-facing contract early: register names, command bits,
mode identifiers, length registers, stream semantics, tag registers, and timeout
handling. The RTL wrapper can now be written against a known firmware interface.

## Frozen MMIO ABI

The software-visible register map is frozen in:

- `ascon_arch/register_map.py` — source of truth
- `firmware/ascon_accel/ascon_accel_regs.h` — generated C constants
- `rtl/common/ascon_accel_regs.vh` — generated Verilog constants
- `docs/ascon_accel_register_map.md` — generated ABI document

Regenerate these files with:

```bash
python tools/generate_accel_regs.py
```

Firmware must check `ASCON_REG_ABI_VERSION` and `ASCON_REG_CAPABILITIES` before using optional modes. Faster or board-specific RTL implementations should preserve this ABI and only change latency/throughput.
