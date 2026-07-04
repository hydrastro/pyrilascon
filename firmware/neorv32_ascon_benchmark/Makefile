APP_SRC = main.c \
  ../ascon_accel/ascon_accel.c \
  ../ascon_accel/ascon_accel_control.c \
  ../ascon_accel/ascon_accel_caps.c \
  ../ascon_accel/ascon_accel_mmio_data.c \
  ../ascon_accel/ascon_accel_axis_data.c \
  ../ascon_accel/ascon_accel_benchmark.c \
  ../ascon_ref/ascon_ref_aead128.c

APP_INC = -I../ascon_accel -I../ascon_ref
override USER_FLAGS += -Wextra

# Set USE_AXIS_MMIO=1 to benchmark the stream-native AEAD128 SoC top through
# the CPU-driven MMIO-to-AXI-stream bridge transport.
#
# Set USE_CFS_AXIS_MMIO=1 for the single-CFS-window stream wrapper in
# rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd. That wrapper maps the
# frozen CSR window at ASCON_ACCEL_BASE_ADDR and the AXI bridge at +0x100.
USE_AXIS_MMIO ?= 0
USE_CFS_AXIS_MMIO ?= 0
ifeq ($(USE_CFS_AXIS_MMIO),1)
USE_AXIS_MMIO := 1
AXIS_MMIO_BASE_ADDR ?= 0xFFEB0100u
endif
AXIS_MMIO_BASE_ADDR ?= 0xFFEC0000u
ifeq ($(USE_AXIS_MMIO),1)
APP_SRC += ../ascon_accel/ascon_accel_axis_mmio_transport.c
override USER_FLAGS += -DASCON_BENCH_USE_AXIS_MMIO=1
override USER_FLAGS += -DASCON_ACCEL_AXIS_MMIO_BASE_ADDR=$(AXIS_MMIO_BASE_ADDR)
endif


# Board benchmark images can be slightly larger than the upstream NEORV32
# default ROM setting, especially when the UART report fields and software
# reference implementation are included. Keep the linker configuration explicit
# and board-manifest-friendly instead of relying on common.mk defaults.
NEORV32_ROM_SIZE ?= 32k
NEORV32_RAM_SIZE ?= 16k
NEORV32_HEAP_SIZE ?= 512
override USER_FLAGS += -Wl,--defsym,__neorv32_rom_size=$(NEORV32_ROM_SIZE)
override USER_FLAGS += -Wl,--defsym,__neorv32_ram_size=$(NEORV32_RAM_SIZE)
override USER_FLAGS += -Wl,--defsym,__neorv32_heap_size=$(NEORV32_HEAP_SIZE)


# Freestanding board-safe profile for Nix-native toolchains that can emit
# RV32I/ILP32 code but do not provide a matching soft-float newlib/libgcc.
# The application still uses NEORV32 common.mk for crt0, image generation and
# installation, but it links without libc/libgcc. Keep this mode integer-only.
#
# `override` is essential: when the cosim Makefile invokes this Makefile
# with USER_FLAGS=... on the command line, plain `USER_FLAGS +=` is
# ignored (command-line variables have higher priority than file-level
# assignments). `override` says "append regardless".
#
# -nostdlib       : do not link the standard system startup files or libraries
# -nodefaultlibs  : do not search default library paths (prevents auto-pull
#                   of libgcc.a when the linker resolves __udivdi3 etc.; our
#                   freestanding_runtime.c provides matching soft-float helpers)
# -nostartfiles   : do not use the standard system startup files (crt0 is
#                   already supplied by NEORV32)
FREESTANDING ?= 0
ifeq ($(FREESTANDING),1)
APP_SRC += freestanding_runtime.c
override USER_FLAGS += -DASCON_BENCH_FREESTANDING=1
override USER_FLAGS += -ffreestanding -fno-builtin -fno-stack-protector
override USER_FLAGS += -nostdlib -nostartfiles -nodefaultlibs
# Belt-and-braces: force the link to skip libgcc even if gcc's driver
# decides to add it back. -Wl,--no-undefined would surface the issue
# clearly if our freestanding_runtime.c is missing a symbol.
override USER_FLAGS += -Wl,--no-warn-mismatch
endif

ifeq ($(NEORV32_HOME),)
$(error Set NEORV32_HOME to a resolved NEORV32 checkout; use `make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware`)
endif

include $(NEORV32_HOME)/sw/common/common.mk
