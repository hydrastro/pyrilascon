APP_SRC = main.c \
  ../ascon_accel/ascon_accel.c \
  ../ascon_accel/ascon_accel_control.c \
  ../ascon_accel/ascon_accel_caps.c \
  ../ascon_accel/ascon_accel_mmio_data.c \
  ../ascon_accel/ascon_accel_axis_data.c \
  ../ascon_accel/ascon_accel_benchmark.c \
  ../ascon_ref/ascon_ref_aead128.c

APP_INC = -I../ascon_accel -I../ascon_ref
USER_FLAGS += -Wextra

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
USER_FLAGS += -DASCON_BENCH_USE_AXIS_MMIO=1
USER_FLAGS += -DASCON_ACCEL_AXIS_MMIO_BASE_ADDR=$(AXIS_MMIO_BASE_ADDR)
endif


# Board benchmark images can be slightly larger than the upstream NEORV32
# default ROM setting, especially when the UART report fields and software
# reference implementation are included. Keep the linker configuration explicit
# and board-manifest-friendly instead of relying on common.mk defaults.
NEORV32_ROM_SIZE ?= 32k
NEORV32_RAM_SIZE ?= 16k
NEORV32_HEAP_SIZE ?= 512
USER_FLAGS += -Wl,--defsym,__neorv32_rom_size=$(NEORV32_ROM_SIZE)
USER_FLAGS += -Wl,--defsym,__neorv32_ram_size=$(NEORV32_RAM_SIZE)
USER_FLAGS += -Wl,--defsym,__neorv32_heap_size=$(NEORV32_HEAP_SIZE)

ifeq ($(NEORV32_HOME),)
$(error Set NEORV32_HOME to a resolved NEORV32 checkout; from repo root use `make neorv32-stream-build-firmware`)
endif

include $(NEORV32_HOME)/sw/common/common.mk
