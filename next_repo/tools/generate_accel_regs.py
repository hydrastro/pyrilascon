#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ascon_arch.register_map import (
    CAPABILITY_BITS,
    CONTROL_BITS,
    DATA_CTRL_BITS,
    DATA_KEEP_MASK,
    DATA_KEEP_SHIFT,
    ERROR_ENUMS,
    MODE_ENUMS,
    REGISTERS,
    REGISTER_MAP_VERSION,
    STATUS_BITS,
)

C_HEADER = ROOT / "firmware" / "ascon_accel" / "ascon_accel_regs.h"
V_HEADER = ROOT / "rtl" / "common" / "ascon_accel_regs.vh"
DOC = ROOT / "docs" / "ascon_accel_register_map.md"


def bit_mask(bit: int) -> int:
    return 1 << bit


def emit_c_header() -> str:
    lines: list[str] = []
    lines += [
        "#ifndef ASCON_ACCEL_REGS_H",
        "#define ASCON_ACCEL_REGS_H",
        "",
        "#include <stdint.h>",
        "",
        "/* Generated from ascon_arch/register_map.py. Do not edit manually. */",
        f"#define ASCON_ACCEL_ABI_VERSION {REGISTER_MAP_VERSION}u",
        "",
        "/* Register offsets, byte-addressed. */",
    ]
    for reg in REGISTERS:
        lines.append(f"#define ASCON_REG_{reg.name:<17} 0x{reg.offset:02X}u")
    lines.append("")
    lines.append("/* CONTROL bits. */")
    for bit in CONTROL_BITS:
        lines.append(f"#define ASCON_CONTROL_{bit.name:<14} (1u << {bit.bit})")
    lines.append("")
    lines.append("/* STATUS bits. */")
    for bit in STATUS_BITS:
        lines.append(f"#define ASCON_STATUS_{bit.name:<15} (1u << {bit.bit})")
    lines.append("")
    lines.append("/* DATA_IN_CTRL / DATA_OUT_CTRL bits. */")
    for bit in DATA_CTRL_BITS:
        lines.append(f"#define ASCON_DATA_{bit.name:<17} (1u << {bit.bit})")
    lines.append(f"#define ASCON_DATA_KEEP_SHIFT   {DATA_KEEP_SHIFT}u")
    lines.append(f"#define ASCON_DATA_KEEP_MASK    0x{DATA_KEEP_MASK:X}u")
    lines.append("")
    lines.append("/* MODE values. */")
    for enum in MODE_ENUMS:
        lines.append(f"#define ASCON_MODE_{enum.name:<11} {enum.value}u")
    lines.append("")
    lines.append("/* CAPABILITIES bits. */")
    for bit in CAPABILITY_BITS:
        lines.append(f"#define ASCON_CAP_{bit.name:<22} (1u << {bit.bit})")
    lines.append("")
    lines.append("/* ERROR_CODE values. */")
    for enum in ERROR_ENUMS:
        lines.append(f"#define ASCON_ERROR_{enum.name:<18} {enum.value}u")
    lines += ["", "#endif", ""]
    return "\n".join(lines)


def emit_v_header() -> str:
    lines: list[str] = []
    lines += [
        "`ifndef ASCON_ACCEL_REGS_VH",
        "`define ASCON_ACCEL_REGS_VH",
        "",
        "// Generated from ascon_arch/register_map.py. Do not edit manually.",
        f"`define ASCON_ACCEL_ABI_VERSION 32'd{REGISTER_MAP_VERSION}",
        "",
        "// Register offsets, byte-addressed.",
    ]
    for reg in REGISTERS:
        lines.append(f"`define ASCON_REG_{reg.name:<17} 8'h{reg.offset:02X}")
    lines.append("")
    lines.append("// CONTROL bit masks.")
    for bit in CONTROL_BITS:
        lines.append(f"`define ASCON_CONTROL_{bit.name:<14} 32'h{bit_mask(bit.bit):08X}")
    lines.append("")
    lines.append("// STATUS bit masks.")
    for bit in STATUS_BITS:
        lines.append(f"`define ASCON_STATUS_{bit.name:<15} 32'h{bit_mask(bit.bit):08X}")
    lines.append("")
    lines.append("// DATA_IN_CTRL / DATA_OUT_CTRL bit masks.")
    for bit in DATA_CTRL_BITS:
        lines.append(f"`define ASCON_DATA_{bit.name:<17} 32'h{bit_mask(bit.bit):08X}")
    lines.append(f"`define ASCON_DATA_KEEP_SHIFT   {DATA_KEEP_SHIFT}")
    lines.append(f"`define ASCON_DATA_KEEP_MASK    32'h{DATA_KEEP_MASK:08X}")
    lines.append("")
    lines.append("// MODE values.")
    for enum in MODE_ENUMS:
        lines.append(f"`define ASCON_MODE_{enum.name:<11} 4'd{enum.value}")
    lines.append("")
    lines.append("// CAPABILITIES bit masks.")
    for bit in CAPABILITY_BITS:
        lines.append(f"`define ASCON_CAP_{bit.name:<22} 32'h{bit_mask(bit.bit):08X}")
    lines.append("")
    lines.append("// ERROR_CODE values.")
    for enum in ERROR_ENUMS:
        lines.append(f"`define ASCON_ERROR_{enum.name:<18} 32'd{enum.value}")
    lines += ["", "`endif", ""]
    return "\n".join(lines)


def emit_doc() -> str:
    lines: list[str] = []
    lines += [
        "# ASCON Accelerator Register Map",
        "",
        f"ABI version: `{REGISTER_MAP_VERSION}`",
        "",
        "This document freezes the software-visible MMIO ABI for the ASCON accelerator. Future slow, fast, single-core, multi-core, Gowin, or Xilinx implementations should preserve this register map. Hardware may expose fewer algorithms by clearing capability bits.",
        "",
        "All registers are 32-bit little-endian words at byte offsets from the accelerator base address. Multi-word keys, nonces, tags, and data streams use little-endian byte order within each 32-bit word.",
        "",
        "## Register offsets",
        "",
        "| Offset | Name | Access | Description |",
        "|---:|---|---|---|",
    ]
    for reg in REGISTERS:
        lines.append(f"| `0x{reg.offset:02X}` | `ASCON_REG_{reg.name}` | {reg.access} | {reg.description} |")
    lines += ["", "## CONTROL bits", "", "| Bit | Name | Description |", "|---:|---|---|"]
    for bit in CONTROL_BITS:
        lines.append(f"| {bit.bit} | `ASCON_CONTROL_{bit.name}` | {bit.description} |")
    lines += ["", "## STATUS bits", "", "| Bit | Name | Description |", "|---:|---|---|"]
    for bit in STATUS_BITS:
        lines.append(f"| {bit.bit} | `ASCON_STATUS_{bit.name}` | {bit.description} |")
    lines += ["", "## Stream control bits", "", "| Bit | Name | Description |", "|---:|---|---|"]
    for bit in DATA_CTRL_BITS:
        lines.append(f"| {bit.bit} | `ASCON_DATA_{bit.name}` | {bit.description} |")
    lines.append(f"| {DATA_KEEP_SHIFT}..{DATA_KEEP_SHIFT + 3} | `keep` | Four-bit byte-valid mask. Bit 0 corresponds to byte 0 of the 32-bit word. |")
    lines += ["", "## Mode values", "", "| Value | Name | Description |", "|---:|---|---|"]
    for enum in MODE_ENUMS:
        lines.append(f"| {enum.value} | `ASCON_MODE_{enum.name}` | {enum.description} |")
    lines += ["", "## Capability bits", "", "| Bit | Name | Description |", "|---:|---|---|"]
    for bit in CAPABILITY_BITS:
        lines.append(f"| {bit.bit} | `ASCON_CAP_{bit.name}` | {bit.description} |")
    lines += ["", "## Error codes", "", "| Value | Name | Description |", "|---:|---|---|"]
    for enum in ERROR_ENUMS:
        lines.append(f"| {enum.value} | `ASCON_ERROR_{enum.name}` | {enum.description} |")
    lines += [
        "",
        "## Decryption plaintext release policy",
        "",
        "For AEAD decryption, plaintext must not be made visible through `DATA_OUT` until tag verification has succeeded. If verification fails, the implementation must clear or invalidate any internal plaintext buffer and set `ERROR` with `ERROR_CODE = ASCON_ERROR_TAG_INVALID`.",
        "",
        "## Compatibility rule",
        "",
        "Firmware must probe `CAPABILITIES` and `ABI_VERSION` before using optional algorithms or features. A faster accelerator must preserve the observable behavior of this ABI; performance changes should appear only as shorter `BUSY` duration and different cycle-counter values.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    C_HEADER.parent.mkdir(parents=True, exist_ok=True)
    V_HEADER.parent.mkdir(parents=True, exist_ok=True)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    C_HEADER.write_text(emit_c_header())
    V_HEADER.write_text(emit_v_header())
    DOC.write_text(emit_doc())
    print(f"wrote {C_HEADER}")
    print(f"wrote {V_HEADER}")
    print(f"wrote {DOC}")


if __name__ == "__main__":
    main()
