# NEORV32 freestanding board firmware profile

The board-safe firmware profile avoids generic Linux/FHS compatibility layers and
unfree runtime packages. It uses the Nix-native RISC-V compiler to emit
`rv32i_zicsr_zifencei` / `ilp32` code, but links the benchmark as a
freestanding NEORV32 image instead of using newlib/libgcc.

Use:

```bash
nix develop
make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware
make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware-soft
```

This target is intentionally different from `make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware`:

- `make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware` is a host smoke build. On Nix it may select a
  hard/double-float compatibility profile if that is the only newlib multilib.
- `make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware-soft` is the board-safe Nix path. It forces
  RV32I/ILP32 and links without libc/libgcc.

The freestanding profile still uses NEORV32 `common.mk` for the official crt0,
image generator and executable packaging. The benchmark supplies tiny local
`memset`, `memcpy`, `memmove`, `memcmp` and `abort` definitions so it does not
need libc.

Limitations:

- Keep this firmware integer-only.
- Avoid new C library calls unless they are provided by
  `firmware/neorv32_ascon_benchmark/freestanding_runtime.c`.
- Speedup fields remain present for UART parser compatibility, but the
  freestanding build avoids 64-bit division-heavy formatting.
