# NEORV32 soft-float toolchain

The normal board-safe NEORV32 firmware target is RV32I with the ILP32 soft-float ABI. The NEORV32 software flow uses a RISC-V bare-metal GCC toolchain, and minimal soft-core configurations should prefer the integer-only RV32I/ILP32 profile.

Some package-manager RISC-V toolchains, including the Nix toolchain used by the development shell, may only provide a hard/double-float newlib multilib. That can be useful for host build smoke tests, but it is not the preferred release profile for a Tang Nano soft-core build.

The host-smoke build is:

```bash
make neorv32-fetch
make neorv32-stream-build-firmware
```

If the toolchain probe selects `hardfloat-nix`, treat the produced image as a build-system smoke test only unless the NEORV32 hardware configuration actually implements the required F/D ISA profile.

## Board-safe soft-float build

The board-safe firmware target is:

```bash
make neorv32-fetch
make neorv32-soft-toolchain-fetch
make neorv32-stream-build-firmware-soft
```

This downloads/extracts the official NEORV32-compatible `riscv32-unknown-elf` RV32I/ILP32 prebuilt toolchain into `external/` and builds the benchmark firmware with:

```text
MARCH=rv32i_zicsr_zifencei
MABI=ilp32
```

## NixOS note

The official NEORV32 prebuilt RV32I/ILP32 toolchain is distributed as generic Linux dynamically linked binaries. On NixOS those binaries may not execute in a plain `nix develop` shell because the usual dynamic-loader path is intentionally absent.

The repository does **not** add unfree compatibility packages automatically. In particular, the flake does not depend on `steam-run`.

For NixOS there are three practical options:

1. Use `make neorv32-stream-build-firmware` for local host smoke testing with the free Nix-provided RISC-V toolchain.
2. Provide an executable soft-float toolchain yourself, for example via system-level `nix-ld`, an FHS shell, a distro/container environment, or a locally built multilib RISC-V GCC.
3. Run the board-safe soft-float build on a non-NixOS Linux host where the official prebuilt toolchain executes normally.

The helper reports NixOS `stub-ld` failures explicitly so the problem is not mistaken for an ASCON or NEORV32 source issue.
