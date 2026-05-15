# pyrilascon ASCON accelerator files for NEORV32 CFS integration.
#
# Usage:
#   1. Add the normal NEORV32 rtl/core files to the VHDL library `neorv32`.
#   2. Do NOT compile the stock rtl/core/neorv32_cfs.vhd template.
#   3. Compile rtl/neorv32/neorv32_cfs_ascon.vhd into library `neorv32` instead.
#   4. Compile the Verilog files below as regular design sources.

rtl/common/ascon_accel_regs.vh
rtl/common/ascon_round_comb.v
rtl/common/ascon_aead128_mmio_backend.v
rtl/common/ascon_accel_mmio_regs.v
rtl/common/ascon_accel_mmio_aead128_top.v
rtl/neorv32/neorv32_cfs_ascon.vhd
