# NEORV32 CFS integration plan

This project freezes the ASCON accelerator software ABI as a 32-bit MMIO register
map. On NEORV32, the intended integration point is the Custom Functions
Subsystem (CFS), whose registers are CPU-accessible as normal memory-mapped
32-bit words.

## Addressing

The firmware driver defaults to the NEORV32 CFS base address:

```c
#define ASCON_ACCEL_BASE_ADDR 0xFFEB0000u
```

The ASCON register offsets are defined in:

- `firmware/ascon_accel/ascon_accel_regs.h`
- `rtl/common/ascon_accel_regs.vh`

Both generated headers come from the same Python source:

- `ascon_arch/register_map.py`

## Integration layers

Current layers:

1. `rtl/common/ascon_accel_mmio_regs.v` implements the frozen software-visible
   register bank and exposes a clean internal core interface.
2. `rtl/common/ascon_accel_core_stub.v` is a non-cryptographic stub used only to
   validate the MMIO ABI and firmware flow.
3. `rtl/common/ascon_accel_mmio_stub_top.v` wires the register bank to the stub.
4. The next real backend will replace the stub with an ASCON-AEAD128 core.

## NEORV32 CFS replacement strategy

NEORV32's CFS provides a large array of 32-bit memory-mapped registers. The
cleanest integration is to adapt CFS register accesses to the simple bus used by
`ascon_accel_mmio_regs.v`:

```text
CFS REG[index] write/read
  -> byte offset = index * 4
  -> bus_addr_i  = byte offset[7:0]
  -> bus_write_i = write enable
  -> bus_valid_i = read or write access
```

The CFS wrapper should map the first 128 bytes of the CFS register space to the
frozen ASCON ABI.

## Decryption rule

The ABI requires that decrypted plaintext is not visible through `DATA_OUT`
until tag verification has succeeded. The real decrypt backend must therefore
buffer plaintext internally and release it only when `STATUS.TAG_VALID` is set.

## Current status

The MMIO register bank is ready. The cryptographic backend behind it is still a
stub. This is intentional: the next step is to bind the already working
standalone AEAD128 slow/KAT core to this ABI.
