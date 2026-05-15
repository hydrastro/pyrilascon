# NEORV32 ASCON accelerator firmware demo

This is a firmware scaffold for the frozen ASCON accelerator ABI.

It is intended to be copied into a NEORV32 software project once the CFS wrapper
is integrated into the hardware design. It uses the shared driver in
`firmware/ascon_accel/`.

Current status:

- The driver and register definitions compile as host C.
- This demo references `neorv32.h`, so it is meant for the NEORV32 software tree.
- The hardware-side MMIO register bank exists in `rtl/common/ascon_accel_mmio_regs.v`.
- The cryptographic CFS backend is still to be connected to the real AEAD128 core.

The demo checks:

1. ABI version.
2. Hardware capabilities.
3. AEAD128 availability.
4. One encrypt call through the software driver.
