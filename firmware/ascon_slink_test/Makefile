# Ascon-AEAD128 accelerator -- SLINK data-plane self-test.
#
# Runs on the STREAM SoC only (make soc-build-slink). On the MMIO bitstream it
# will report CAPABILITIES bit 23 clear and stop.
#
# Mirrors firmware/neorv32_ascon_benchmark/Makefile (the configuration that is
# known to build and run on the Tang Nano 20K); only APP_SRC differs -- the
# benchmark harness is not needed here.
#
# Build (inside `nix develop`):
#     make -C firmware/ascon_slink_test FREESTANDING=1 exe
# Upload:
#     python host/neorv32_upload.py <port> firmware/ascon_slink_test/neorv32_exe.bin slink.log

APP_SRC = main.c \
  ../ascon_slink/ascon_slink.c

APP_INC = -I../ascon_slink
override USER_FLAGS += -Wextra

# MUST match the SoC's IMEM/DMEM (rtl/soc/neorv32_ascon_soc.vhd: IMEM_SIZE=16K,
# DMEM_SIZE=8K). If these exceed the real memory, crt0 places the stack past the
# end of DMEM and the CPU traps before main() -- a silent hang.
NEORV32_ROM_SIZE ?= 16k
NEORV32_RAM_SIZE ?= 8k
NEORV32_HEAP_SIZE ?= 512
override USER_FLAGS += -Wl,--defsym,__neorv32_rom_size=$(NEORV32_ROM_SIZE)
override USER_FLAGS += -Wl,--defsym,__neorv32_ram_size=$(NEORV32_RAM_SIZE)
override USER_FLAGS += -Wl,--defsym,__neorv32_heap_size=$(NEORV32_HEAP_SIZE)

# Freestanding profile: the Nix toolchain emits RV32I/ILP32 but has no matching
# soft-float newlib/libgcc. Link without libc/libgcc; freestanding_runtime.c
# supplies memset/memcpy/memcmp and the integer helpers.
FREESTANDING ?= 0
ifeq ($(FREESTANDING),1)
APP_SRC += freestanding_runtime.c
override USER_FLAGS += -DASCON_BENCH_FREESTANDING=1
override USER_FLAGS += -ffreestanding -fno-builtin -fno-stack-protector
override USER_FLAGS += -nostdlib -nostartfiles -nodefaultlibs
override USER_FLAGS += -Wl,--no-warn-mismatch
endif

# Auto-detect the RISC-V toolchain prefix (nixpkgs uses riscv32-none-elf-,
# NEORV32 defaults to riscv-none-elf-). Override with RISCV_PREFIX=... if needed.
DETECTED_RISCV_PREFIX := $(shell for p in riscv32-none-elf- riscv-none-elf- riscv64-none-elf- riscv64-unknown-elf- riscv32-unknown-elf- riscv-none-embed-; do command -v $${p}gcc >/dev/null 2>&1 && { echo $$p; break; }; done)
ifneq ($(DETECTED_RISCV_PREFIX),)
RISCV_PREFIX ?= $(DETECTED_RISCV_PREFIX)
endif

ifeq ($(NEORV32_HOME),)
$(error Set NEORV32_HOME to a resolved NEORV32 checkout (the `nix develop` shell sets it))
endif

# NEORV32 builds image_gen into $NEORV32_HOME/sw/image_gen, which is read-only
# when NEORV32 is a Nix store path. Redirect it into our writable build dir.
$(shell mkdir -p $(CURDIR)/build)
override IMAGE_GEN = $(CURDIR)/build/image_gen

include $(NEORV32_HOME)/sw/common/common.mk
