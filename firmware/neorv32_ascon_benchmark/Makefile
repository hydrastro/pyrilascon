APP_SRC = main.c \
  ../ascon_accel/ascon_accel.c \
  ../ascon_accel/ascon_accel_control.c \
  ../ascon_accel/ascon_accel_caps.c \
  ../ascon_accel/ascon_accel_mmio_data.c \
  ../ascon_accel/ascon_accel_axis_data.c \
  ../ascon_accel/ascon_accel_benchmark.c \
  ../ascon_ref/ascon_ref_aead128.c

APP_INC = -I../ascon_accel -I../ascon_ref
APP_CFLAGS += -Wall -Wextra

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
APP_CFLAGS += -DASCON_BENCH_USE_AXIS_MMIO=1
APP_CFLAGS += -DASCON_ACCEL_AXIS_MMIO_BASE_ADDR=$(AXIS_MMIO_BASE_ADDR)
endif

ifeq ($(NEORV32_HOME),)
$(error Set NEORV32_HOME to a resolved NEORV32 checkout; from repo root use `make neorv32-stream-build-firmware`)
endif

include $(NEORV32_HOME)/sw/common/common.mk
