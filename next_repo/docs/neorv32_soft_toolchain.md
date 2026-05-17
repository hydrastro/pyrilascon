# NEORV32 soft-float firmware toolchains

The board hardware profile should use `rv32i_zicsr_zifencei` with the `ilp32`
soft-float ABI. Some package-manager toolchains, including the Nix toolchain
available in the development shell, can compile that ISA but do not ship a
matching soft-float newlib/libgcc multilib.

The project therefore provides two firmware build paths:

```bash
make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware
```

This is a host smoke build. It probes the available toolchain and may select a
`hardfloat-nix` compatibility profile if that is the only linkable newlib/libgcc
profile. Treat this as a smoke test only / host-toolchain sanity check, not the preferred
final board profile.

```bash
make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware-soft
```

This is the Nix-native board-safe path. It forces `rv32i_zicsr_zifencei` /
`ilp32` and uses a freestanding link so it does not depend on newlib/libgcc, FHS
compatibility, `nix-ld`, or unfree helpers such as `steam-run`.

The freestanding build still uses the official NEORV32 `common.mk` for startup,
linker layout, image generation and executable packaging. The benchmark supplies
a tiny local runtime in `firmware/neorv32_ascon_benchmark/freestanding_runtime.c`
for functions such as `memset` and `memcpy`.

The optional `make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware-soft` target still downloads the
official upstream RV32I/ILP32 toolchain into `external/`. On NixOS that binary
may fail with the standard `stub-ld` message because it is a generic dynamically
linked Linux executable. The repo does not attempt to run it through FHS wrappers
or unfree runtime packages.

The Nix-native freestanding target does not depend on `steam-run`.
