# NEORV32 ASCON accelerator firmware demo skeleton.
#
# This Makefile is intended to be used from inside a NEORV32 software tree or
# with NEORV32_HOME pointing at a checked-out NEORV32 repository.
#
# Example:
#   make NEORV32_HOME=/path/to/neorv32

NEORV32_HOME ?= ../../external/neorv32
APP_SRC      += main.c \
                ../ascon_accel/ascon_accel.c \
                ../ascon_accel/ascon_accel_control.c \
                ../ascon_accel/ascon_accel_caps.c \
                ../ascon_accel/ascon_accel_mmio_data.c \
                ../ascon_accel/ascon_accel_axis_data.c
APP_INC      += -I../ascon_accel
APP_CFLAGS   += -Wall -Wextra

include $(NEORV32_HOME)/sw/common/common.mk
