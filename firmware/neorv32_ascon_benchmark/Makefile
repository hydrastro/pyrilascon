APP_SRC = main.c \
  ../ascon_accel/ascon_accel.c \
  ../ascon_accel/ascon_accel_control.c \
  ../ascon_accel/ascon_accel_caps.c \
  ../ascon_accel/ascon_accel_mmio_data.c \
  ../ascon_accel/ascon_accel_axis_data.c \
  ../ascon_accel/ascon_accel_benchmark.c \
  ../ascon_ref/ascon_ref_aead128.c

APP_INC = -I../ascon_accel -I../ascon_ref

ifeq ($(NEORV32_HOME),)
$(error Set NEORV32_HOME=/path/to/neorv32 before invoking this Makefile)
endif

include $(NEORV32_HOME)/sw/common/common.mk
