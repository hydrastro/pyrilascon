# NEORV32 firmware toolchain profiles

The NEORV32 stream benchmark firmware is built through the upstream
`sw/common/common.mk` flow, but the project-level target probes the local
RISC-V GCC before invoking it:

```bash
make neorv32-toolchain-check
make neorv32-stream-build-firmware
```

The default profile is:

```make
NEORV32_FW_PROFILE=auto
```

`auto` tries profiles in this order:

1. **soft**: hardware-correct NEORV32 RV32I/ILP32
2. **hardfloat-nix**: explicit hard/double-float compatibility candidates for
   package-manager toolchains
3. **toolchain-default**: the compiler's own default target, with `MARCH`/`MABI`
   recovered from `gcc -Q --help=target`

The preferred profile for final hardware release is still:

```text
MARCH=rv32i_zicsr_zifencei
MABI=ilp32
```

However, some Nixpkgs embedded RISC-V toolchains do not ship a matching
soft-float newlib/libgcc multilib. In that case the probe can fall back to a
compatibility profile. The benchmark code itself is integer-only, so this can be
useful for local board bring-up, but a true soft-float multilib toolchain should
be used for final reproducible release measurements.

Useful commands:

```bash
make neorv32-toolchain-check
make neorv32-toolchain-check NEORV32_FW_PROFILE=soft
make neorv32-toolchain-check NEORV32_FW_PROFILE=hardfloat-nix
make neorv32-toolchain-check NEORV32_FW_PROFILE=toolchain-default
make neorv32-toolchain-check NEORV32_FW_PROFILE=auto
make neorv32-stream-build-firmware
```

For diagnostics, run:

```bash
PYTHONPATH=. python tools/check_neorv32_toolchain.py --verbose
```

The verbose mode prints the last linker error for each attempted profile. This
is useful for distinguishing a missing compiler from an ABI/multilib mismatch
such as `can't link double-float modules with soft-float modules`.

The firmware Makefile also configures the NEORV32 linker memory sizes
explicitly:

```make
NEORV32_ROM_SIZE ?= 32k
NEORV32_RAM_SIZE ?= 16k
NEORV32_HEAP_SIZE ?= 512
```

The previous default ROM size was too small for the UART benchmark plus software
reference implementation on the current toolchain.

Implementation note: the probe links a tiny `main()` with `-nostartfiles` and
`-Wl,-e,main`. It intentionally does **not** use `--no-entry`, because GNU
`ld.bfd` used by common embedded RISC-V toolchains does not accept that option.

## Image-generation tools

The firmware build does not stop at `riscv-none-elf-gcc`. Upstream NEORV32
`common.mk` also invokes binutils programs such as `riscv-none-elf-readelf`,
`riscv-none-elf-objcopy`, and `riscv-none-elf-size` while producing the final
`neorv32_exe.bin` image. The Nix development shell therefore creates
`riscv-none-elf-*` compatibility wrappers for these binutils as well as the
compiler. The toolchain probe treats these programs as required so a missing
`readelf` wrapper is reported before the firmware build reaches image
generation.
