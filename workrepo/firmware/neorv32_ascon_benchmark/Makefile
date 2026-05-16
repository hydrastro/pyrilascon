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
USE_AXIS_MMIO ?= 0
ifeq ($(USE_AXIS_MMIO),1)
APP_SRC += ../ascon_accel/ascon_accel_axis_mmio_transport.c
APP_CFLAGS += -DASCON_BENCH_USE_AXIS_MMIO=1
endif

ifeq ($(NEORV32_HOME),)
$(error Set NEORV32_HOME=/path/to/neorv32 before invoking this Makefile)
endif

include $(NEORV32_HOME)/sw/common/common.mk
