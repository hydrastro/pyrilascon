# pyrilascon stream-native ASCON accelerator files for NEORV32 CFS integration.
#
# Usage:
#   1. Add the normal NEORV32 rtl/core files to the VHDL library `neorv32`.
#   2. Do NOT compile the stock rtl/core/neorv32_cfs.vhd template.
#   3. Compile rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd into library `neorv32`.
#   4. Compile the Verilog files below as regular design sources.
#
# CFS-relative address map:
#   0x000..0x0ff -> frozen ASCON CSR/MMIO ABI
#   0x100..0x1ff -> CPU-driven AXI-stream MMIO bridge

rtl/common/ascon_accel_regs.vh
rtl/common/ascon_round_comb.v
rtl/common/ascon_accel_mmio_regs.v
rtl/stream/ascon_aead128_stream_encrypt.v
rtl/stream/ascon_aead128_stream_decrypt_buffered.v
rtl/stream/ascon_aead128_stream.v
rtl/common/ascon_accel_stream_aead128_top.v
rtl/common/ascon_axis_mmio_bridge.v
rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v
rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd
