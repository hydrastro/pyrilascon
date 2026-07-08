NEORV32_ROM_SIZE ?= 16k
NEORV32_RAM_SIZE ?= 8k
NEORV32_HEAP_SIZE ?= 512
EFFORT ?= -Os
override USER_FLAGS += -Wl,--defsym,__neorv32_rom_size=$(NEORV32_ROM_SIZE)
override USER_FLAGS += -Wl,--defsym,__neorv32_ram_size=$(NEORV32_RAM_SIZE)
override USER_FLAGS += -Wl,--defsym,__neorv32_heap_size=$(NEORV32_HEAP_SIZE)

APP_SRC = main.c

FREESTANDING ?= 0
ifeq ($(FREESTANDING),1)
APP_SRC += ../neorv32_ascon_benchmark/freestanding_runtime.c
override USER_FLAGS += -ffreestanding -fno-builtin -fno-stack-protector
override USER_FLAGS += -nostdlib -nostartfiles -nodefaultlibs
override USER_FLAGS += -Wl,--no-warn-mismatch
endif

# Auto-detect the RISC-V toolchain prefix (nixpkgs: riscv32-none-elf-).
DETECTED_RISCV_PREFIX := $(shell for p in riscv32-none-elf- riscv-none-elf- riscv64-none-elf- riscv64-unknown-elf- riscv32-unknown-elf- riscv-none-embed-; do command -v $${p}gcc >/dev/null 2>&1 && { echo $$p; break; }; done)
ifneq ($(DETECTED_RISCV_PREFIX),)
RISCV_PREFIX ?= $(DETECTED_RISCV_PREFIX)
endif

ifeq ($(NEORV32_HOME),)
$(error Set NEORV32_HOME - run inside `nix develop`)
endif

# Redirect NEORV32's image_gen build into our writable dir (Nix store is read-only).
$(shell mkdir -p $(CURDIR)/build)
override IMAGE_GEN = $(CURDIR)/build/image_gen

include $(NEORV32_HOME)/sw/common/common.mk
