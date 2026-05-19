# ASCON-on-NEORV32 open-source co-simulation
REPO_ROOT     ?= $(realpath ../../../..)
NEORV32_HOME  ?= $(REPO_ROOT)/external/neorv32
RISCV_PREFIX  ?= riscv-none-elf-
SIMULATOR     ?= iverilog

BUILD   := build
WRAPPER := neorv32_verilog_wrapper

NEORV32_FFILE       := $(shell cat $(NEORV32_HOME)/rtl/file_list_soc.f)
NEORV32_SRCS        := $(subst NEORV32_RTL_PATH_PLACEHOLDER,$(NEORV32_HOME)/rtl,$(NEORV32_FFILE))
NEORV32_SRCS_NOCFS  := $(filter-out %/neorv32_cfs.vhd,$(NEORV32_SRCS))

ASCON_CFS_VHDL := $(REPO_ROOT)/rtl/neorv32/neorv32_cfs_ascon.vhd

ASCON_VLOG := \
  $(REPO_ROOT)/rtl/common/ascon_round_comb.v \
  $(REPO_ROOT)/rtl/common/ascon_aead128_mmio_backend.v \
  $(REPO_ROOT)/rtl/common/ascon_accel_mmio_regs.v \
  $(REPO_ROOT)/rtl/common/ascon_accel_mmio_aead128_top.v

FW_DIR      := $(REPO_ROOT)/firmware/neorv32_ascon_benchmark
FW_IMAGE    := $(FW_DIR)/neorv32_imem_image.vhd
IMEM_TARGET := $(NEORV32_HOME)/rtl/core/neorv32_imem_image.vhd
IMEM_BACKUP := $(NEORV32_HOME)/rtl/core/neorv32_imem_image.vhd.orig

.PHONY: all firmware-image install-image clean sim run parse-log restore-image netlist

all: run

firmware-image:
	$(MAKE) -C $(FW_DIR) \
	  NEORV32_HOME=$(NEORV32_HOME) RISCV_PREFIX=$(RISCV_PREFIX) \
	  MARCH=rv32i_zicsr_zifencei MABI=ilp32 \
	  FREESTANDING=1 LD_LIBS= USER_LIBS= \
	  clean_all image

install-image: firmware-image
	@if [ ! -f $(IMEM_BACKUP) ]; then cp $(IMEM_TARGET) $(IMEM_BACKUP); fi
	cp $(FW_IMAGE) $(IMEM_TARGET)
	@echo "Installed firmware image:"
	@grep image_size_c $(IMEM_TARGET)

restore-image:
	@if [ -f $(IMEM_BACKUP) ]; then cp $(IMEM_BACKUP) $(IMEM_TARGET); echo "Restored upstream IMEM image."; else echo "No backup."; fi

$(WRAPPER).v: $(WRAPPER).vhd install-image
	@mkdir -p $(BUILD)
	ghdl -i --std=08 --work=neorv32 --workdir=$(BUILD) -P$(BUILD) \
	  $(NEORV32_SRCS_NOCFS) \
	  $(ASCON_CFS_VHDL) \
	  $(WRAPPER).vhd
	ghdl -m --std=08 --work=neorv32 --workdir=$(BUILD) -P$(BUILD) $(WRAPPER)
	ghdl synth --std=08 --work=neorv32 --workdir=$(BUILD) -P$(BUILD) \
	  --out=verilog $(WRAPPER) > $(WRAPPER).v

netlist: $(WRAPPER).v

sim: $(WRAPPER).v
ifeq ($(SIMULATOR),iverilog)
	@echo "Compiling with Icarus Verilog"
	iverilog -g2012 -I $(REPO_ROOT)/rtl/common -o $(BUILD)/neorv32-iverilog testbench.v $(WRAPPER).v $(ASCON_VLOG)
	@echo "Running:"
	vvp $(BUILD)/neorv32-iverilog
else ifeq ($(SIMULATOR),verilator)
	@echo "Compiling with Verilator"
	verilator -Wno-fatal -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-CASEINCOMPLETE -Wno-UNOPTFLAT --binary --top-module neorv32_ascon_tb +incdir+$(REPO_ROOT)/rtl/common --Mdir $(BUILD)/obj_dir testbench.v $(WRAPPER).v $(ASCON_VLOG)
	@echo "Running:"
	$(BUILD)/obj_dir/Vneorv32_ascon_tb
else
	$(error Unsupported SIMULATOR=$(SIMULATOR). Use iverilog or verilator)
endif

run: sim parse-log

parse-log:
	@if [ -s neorv32_ascon_tb.log ]; then cd $(REPO_ROOT) && PYTHONPATH=. python tools/parse_neorv32_ascon_uart_log.py $(CURDIR)/neorv32_ascon_tb.log --markdown --out $(CURDIR)/cosim_report.md; echo ""; echo "Report: $(CURDIR)/cosim_report.md"; cat $(CURDIR)/cosim_report.md; else echo "No UART log captured."; fi

clean:
	rm -rf $(BUILD) $(WRAPPER).v neorv32_ascon_tb.log cosim_report.md
