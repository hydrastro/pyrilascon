# Tang Nano 20K: NEORV32 RV32I software baseline + ASCON-AEAD128 MMIO accelerator

SHELL := /bin/bash
.DEFAULT_GOAL := help
.DELETE_ON_ERROR:

REPO_ROOT := $(abspath $(CURDIR)/../../..)
TOP := tangnano20k_neorv32_mmio_top
DEVICE := GW2AR-LV18QN88C8/I7
YOSYS_FAMILY := gw2a
PNR_FAMILY := GW2A-18C
FREQ_MHZ := 27
CST := $(CURDIR)/tangnano20k_neorv32_mmio.cst
BUILD := $(REPO_ROOT)/build/neorv32_mmio_20k
NEORV32_HOME ?= $(REPO_ROOT)/external/neorv32

GHDL ?= ghdl
YOSYS ?= $(shell command -v yowasp-yosys 2>/dev/null || command -v yosys 2>/dev/null || echo yowasp-yosys)
NEXTPNR ?= $(shell command -v yowasp-nextpnr-himbaechel-gowin 2>/dev/null || command -v nextpnr-himbaechel 2>/dev/null || echo yowasp-nextpnr-himbaechel-gowin)
GOWIN_PACK ?= gowin_pack
OPENFPGALOADER ?= openFPGALoader
RISCV_PREFIX ?= riscv-none-elf-
NEORV32_FW_PROFILE ?= auto
SERIAL ?=
BAUD ?= 19200
UART_TIMEOUT ?= 60
LOG ?= $(CURDIR)/uart_mmio.log

ASCON_VERILOG_SRCS := \
  $(REPO_ROOT)/rtl/common/ascon_accel_regs.vh \
  $(REPO_ROOT)/rtl/common/ascon_round_comb.v \
  $(REPO_ROOT)/rtl/common/ascon_aead128_mmio_backend.v \
  $(REPO_ROOT)/rtl/common/ascon_accel_mmio_regs.v \
  $(REPO_ROOT)/rtl/common/ascon_accel_mmio_aead128_top.v

NEORV32_RTL := $(NEORV32_HOME)/rtl
NEORV32_FILE_LIST := $(NEORV32_RTL)/file_list_soc.f
NEORV32_FF := $(shell cat $(NEORV32_FILE_LIST) 2>/dev/null)
NEORV32_ALL := $(subst NEORV32_RTL_PATH_PLACEHOLDER,$(NEORV32_RTL),$(NEORV32_FF))
NEORV32_VHDL_SRCS := $(filter-out %/neorv32_cfs.vhd,$(NEORV32_ALL))
ASCON_CFS_VHDL := $(REPO_ROOT)/rtl/neorv32/neorv32_cfs_ascon.vhd
BOARD_TOP_VHDL := $(CURDIR)/rtl/$(TOP).vhd
VHDL_SRCS := $(NEORV32_VHDL_SRCS) $(ASCON_CFS_VHDL) $(BOARD_TOP_VHDL)

FW_DIR := $(REPO_ROOT)/firmware/neorv32_ascon_benchmark
FW_INPUTS := \
  $(wildcard $(FW_DIR)/*.c $(FW_DIR)/*.h) \
  $(wildcard $(REPO_ROOT)/firmware/ascon_accel/*.c $(REPO_ROOT)/firmware/ascon_accel/*.h) \
  $(wildcard $(REPO_ROOT)/firmware/ascon_ref/*.c $(REPO_ROOT)/firmware/ascon_ref/*.h)
FW_STAMP := $(BUILD)/.firmware-installed
IMEM_IMAGE := $(NEORV32_HOME)/rtl/core/neorv32_imem_image.vhd

GHDL_DIR := $(BUILD)/ghdl
GHDL_V := $(BUILD)/$(TOP)_ghdl.v
JSON := $(BUILD)/$(TOP).json
PNR_JSON := $(BUILD)/$(TOP)_pnr.json
PNR_REPORT := $(BUILD)/$(TOP)_pnr_report.json
FS := $(BUILD)/$(TOP).fs
REPORT_MD := $(BUILD)/uart_report.md
REPORT_CSV := $(BUILD)/uart_report.csv
REPORT_JSON := $(BUILD)/uart_report.json

.PHONY: help doctor sanity test firmware firmware-rebuild ghdl bitstream rebuild \
        detect prog-sram prog-flash uart-capture uart-report benchmark \
        clean clean-firmware print-artifacts

help:
	@echo "Tang Nano 20K NEORV32 + ASCON targets"
	@echo ""
	@echo "  make doctor       Fail-fast dependency and checkout checks"
	@echo "  make sanity       Focused source/configuration tests"
	@echo "  make firmware     Build and install the embedded NEORV32 image"
	@echo "  make bitstream    Firmware + GHDL + Yosys + nextpnr + gowin_pack"
	@echo "  make rebuild      Clean board build and regenerate the bitstream"
	@echo "  make detect       Detect the FPGA/JTAG chain"
	@echo "  make prog-sram    Build and load volatile SRAM"
	@echo "  make prog-flash   Build and write persistent external flash"
	@echo "  make uart-capture Capture one complete PASS/FAIL run automatically"
	@echo "  make uart-report  Validate the log and emit Markdown/CSV/JSON"
	@echo "  make benchmark    Capture followed by strict report generation"
	@echo ""
	@echo "Variables: SERIAL=/dev/serial/by-id/... BAUD=19200 UART_TIMEOUT=60"

$(BUILD):
	@mkdir -p "$@"

doctor:
	@set -euo pipefail; \
	  test -f "$(REPO_ROOT)/flake.nix" || { echo "error: invalid REPO_ROOT=$(REPO_ROOT)"; exit 1; }; \
	  test -f "$(NEORV32_FILE_LIST)" || { echo "error: missing pinned NEORV32 checkout; run 'nix develop' from this repository"; exit 1; }; \
	  test -f "$(CST)" || { echo "error: missing constraints: $(CST)"; exit 1; }; \
	  test -f "$(BOARD_TOP_VHDL)" || { echo "error: missing board top: $(BOARD_TOP_VHDL)"; exit 1; }; \
	  for cmd in "$(GHDL)" "$(YOSYS)" "$(NEXTPNR)" "$(GOWIN_PACK)" "$(OPENFPGALOADER)" "$(RISCV_PREFIX)gcc" "$(RISCV_PREFIX)readelf"; do \
	    command -v "$$cmd" >/dev/null || { echo "error: missing tool: $$cmd"; exit 1; }; \
	  done; \
	  cd "$(REPO_ROOT)"; \
	  python -c 'import apycula, serial; print("Python FPGA packages: OK")'; \
	  PYTHONPATH=. python tools/check_neorv32_toolchain.py --prefix "$(RISCV_PREFIX)" --profile "$(NEORV32_FW_PROFILE)" --check; \
	  echo "Tang Nano 20K toolchain and dependency checks: PASS"

sanity: doctor
	@cd "$(REPO_ROOT)" && env -u NEORV32_HOME PYTHONPATH=. pytest -q \
	  tests/test_firmware_reference_and_benchmark.py \
	  tests/test_portable_bringup_dependencies.py \
	  tests/test_tangnano20k_neorv32_mmio_target.py \
	  tests/test_tangnano20k_sweep_report.py

firmware: $(FW_STAMP)

$(FW_STAMP): $(FW_INPUTS) $(FW_DIR)/Makefile | $(BUILD)
	@set -euo pipefail; \
	  test -f "$(NEORV32_FILE_LIST)" || { echo "error: run 'nix develop' to materialize NEORV32"; exit 1; }; \
	  cd "$(REPO_ROOT)"; \
	  PYTHONPATH=. python tools/check_neorv32_toolchain.py \
	    --prefix "$(RISCV_PREFIX)" --profile "$(NEORV32_FW_PROFILE)" --check; \
	  TOOLCHAIN_ARGS="$$(PYTHONPATH=. python tools/check_neorv32_toolchain.py \
	    --prefix "$(RISCV_PREFIX)" --profile "$(NEORV32_FW_PROFILE)" --make-args)"; \
	  $(MAKE) -C firmware/neorv32_ascon_benchmark \
	    NEORV32_HOME="$(NEORV32_HOME)" \
	    RISCV_PREFIX="$(RISCV_PREFIX)" \
	    ASCON_BENCH_BUILD_TAG=tangnano20k-neorv32-mmio \
	    ASCON_BENCH_MAX_BYTES_TAG=32 \
	    NEORV32_ROM_SIZE=32k NEORV32_RAM_SIZE=8k NEORV32_HEAP_SIZE=512 \
	    $$TOOLCHAIN_ARGS clean_all exe install; \
	  test -s "$(IMEM_IMAGE)" || { echo "error: firmware install did not create $(IMEM_IMAGE)"; exit 1; }; \
	  "$(RISCV_PREFIX)size" "$(FW_DIR)/build/main.elf"; \
	  touch "$@"

firmware-rebuild:
	@rm -f "$(FW_STAMP)"
	@$(MAKE) firmware

ghdl: $(GHDL_V)

$(GHDL_V): $(FW_STAMP) $(VHDL_SRCS) | $(BUILD)
	@mkdir -p "$(GHDL_DIR)"
	$(GHDL) -i --std=08 --work=neorv32 --workdir="$(GHDL_DIR)" -P"$(GHDL_DIR)" $(VHDL_SRCS)
	$(GHDL) -m --std=08 --work=neorv32 --workdir="$(GHDL_DIR)" -P"$(GHDL_DIR)" $(TOP)
	$(GHDL) synth --std=08 --work=neorv32 --workdir="$(GHDL_DIR)" -P"$(GHDL_DIR)" --out=verilog $(TOP) > "$@"

$(JSON): $(GHDL_V) $(ASCON_VERILOG_SRCS) | $(BUILD)
	$(YOSYS) -p "read_verilog -I$(REPO_ROOT)/rtl/common $(ASCON_VERILOG_SRCS) $(GHDL_V); synth_gowin -family $(YOSYS_FAMILY) -top $(TOP) -json $(JSON)"

$(PNR_JSON): $(JSON) $(CST) | $(BUILD)
	$(NEXTPNR) --json "$(JSON)" --write "$@" --report "$(PNR_REPORT)" \
	  --freq "$(FREQ_MHZ)" --device "$(DEVICE)" \
	  --vopt family="$(PNR_FAMILY)" --vopt cst="$(CST)"

$(FS): $(PNR_JSON) | $(BUILD)
	$(GOWIN_PACK) -d "$(PNR_FAMILY)" -o "$@" "$<"
	@echo "Bitstream: $@"
	@echo "Timing/utilization report: $(PNR_REPORT)"

bitstream: $(FS)

rebuild: clean bitstream

detect: doctor
	$(OPENFPGALOADER) -b tangnano20k --detect

prog-sram: bitstream
	$(OPENFPGALOADER) -b tangnano20k "$(FS)"

prog-flash: bitstream
	$(OPENFPGALOADER) -b tangnano20k -f "$(FS)"

uart-capture:
	@cd "$(REPO_ROOT)" && PYTHONPATH=. python tools/capture_neorv32_uart.py \
	  $(if $(strip $(SERIAL)),--serial-device "$(SERIAL)",) \
	  --baud "$(BAUD)" --timeout "$(UART_TIMEOUT)" --log "$(LOG)"

uart-report:
	@cd "$(REPO_ROOT)" && PYTHONPATH=. python tools/parse_sweep_log.py \
	  "$(LOG)" --strict --freq-mhz "$(FREQ_MHZ)" --markdown --out "$(REPORT_MD)"
	@cd "$(REPO_ROOT)" && PYTHONPATH=. python tools/parse_sweep_log.py \
	  "$(LOG)" --strict --freq-mhz "$(FREQ_MHZ)" --csv --out "$(REPORT_CSV)"
	@cd "$(REPO_ROOT)" && PYTHONPATH=. python tools/parse_sweep_log.py \
	  "$(LOG)" --strict --freq-mhz "$(FREQ_MHZ)" --json --out "$(REPORT_JSON)"
	@cat "$(REPORT_MD)"

benchmark: uart-capture uart-report

print-artifacts:
	@printf '%s\n' "$(FS)" "$(PNR_REPORT)" "$(LOG)" "$(REPORT_MD)" "$(REPORT_CSV)" "$(REPORT_JSON)"

clean:
	@rm -rf "$(BUILD)"
	@rm -f "$(LOG)"

clean-firmware:
	@if [ -f "$(NEORV32_HOME)/sw/common/common.mk" ]; then \
	  $(MAKE) -C "$(FW_DIR)" NEORV32_HOME="$(NEORV32_HOME)" clean_all; \
	else \
	  rm -rf "$(FW_DIR)/build"; \
	fi
