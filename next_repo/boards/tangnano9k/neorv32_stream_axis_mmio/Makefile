SHELL := /bin/sh
REPO_ROOT := ../../..
MANIFEST := manifest.json
BUILD := build
LOG ?= uart.log
BAUD ?= 19200
SERIAL ?=
NEORV32_DIR ?= external/neorv32
RISCV_PREFIX ?= riscv-none-elf-
NEORV32_FW_PROFILE ?= auto
FIRMWARE_PROFILE ?= auto

# Local Tang Nano 9K NEORV32 bitstream flow.
# TOP_MODE=plain builds a CPU+UART bootloader smoke image.
# TOP_MODE=ascon builds CPU+UART+ASCON-CFS.
TOP_MODE ?= ascon
TOP = tangnano9k_neorv32_$(TOP_MODE)_top
BOARD_BUILD = $(REPO_ROOT)/build/neorv32_stream_axis_mmio/board/$(TOP_MODE)
BITSTREAM ?= $(BOARD_BUILD)/$(TOP).fs
CST := tangnano9k_neorv32_stream_axis_mmio.cst
DEVICE := GW1NR-LV9QN88PC6/I5
FAMILY := GW1N-9C
BOARD := tangnano9k

GHDL ?= ghdl
YOSYS ?= $(shell command -v yowasp-yosys 2>/dev/null || command -v yosys 2>/dev/null || echo yosys)
NEXTPNR ?= $(shell command -v nextpnr-gowin 2>/dev/null || command -v yowasp-nextpnr-himbaechel-gowin 2>/dev/null || command -v nextpnr-himbaechel 2>/dev/null || echo nextpnr-himbaechel)
GOWIN_PACK ?= gowin_pack
OPENFPGALOADER ?= openFPGALoader

NEORV32_RTL = $(REPO_ROOT)/$(NEORV32_DIR)/rtl
NEORV32_FFILE = $(shell cat $(NEORV32_RTL)/file_list_soc.f 2>/dev/null)
NEORV32_VHDL_ALL = $(subst NEORV32_RTL_PATH_PLACEHOLDER,$(NEORV32_RTL),$(NEORV32_FFILE))
NEORV32_VHDL_SRCS = $(if $(filter ascon,$(TOP_MODE)),$(filter-out %/neorv32_cfs.vhd,$(NEORV32_VHDL_ALL)),$(NEORV32_VHDL_ALL))
ASCON_CFS_VHDL = $(if $(filter ascon,$(TOP_MODE)),$(REPO_ROOT)/rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd,)
BOARD_TOP_VHDL = rtl/$(TOP).vhd
VHDL_SRCS = $(NEORV32_VHDL_SRCS) $(ASCON_CFS_VHDL) $(BOARD_TOP_VHDL)
ASCON_VERILOG_SRCS = $(if $(filter ascon,$(TOP_MODE)),$(shell awk 'NF && $$1 !~ /^#/ && $$1 !~ /\.vhd$$/ {print "$(REPO_ROOT)/" $$1}' $(REPO_ROOT)/rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f),)
VHDL_NETLIST = $(BOARD_BUILD)/$(TOP)_ghdl.v
JSON = $(BOARD_BUILD)/$(TOP).json
PNR_JSON = $(BOARD_BUILD)/$(TOP)_pnr.json
FS = $(BOARD_BUILD)/$(TOP).fs
.DEFAULT_GOAL := all

NEORV32_ARG = $(if $(filter command line,$(origin NEORV32_HOME)),--neorv32-home $(NEORV32_HOME),)
SERIAL_ARG = $(if $(SERIAL),--serial-device $(SERIAL),)

.PHONY: help all clean tools deps manifest check preflight package build-plan session gowin-handoff \
        firmware firmware-auto firmware-soft firmware-image-soft bitstream bitstream-plain bitstream-ascon upload \
        uart-report uart-capture doctor rtl-list memory-map prog-sram prog-flash

help:
	@echo "Tang Nano 9K NEORV32 stream ASCON board target"
	@echo ""
	@echo "Workflow:"
	@echo "  make clean && make tools && make && make prog-sram"
	@echo ""
	@echo "Targets:"
	@echo "  make tools                 Check host tools used by this board target"
	@echo "  make deps                  Fetch/check the project-local NEORV32 checkout"
	@echo "  make                       Generate package/handoff, build firmware, and build ASCON bitstream"
	@echo "  make bitstream-plain       Build minimal NEORV32 CPU+UART bootloader smoke bitstream"
	@echo "  make bitstream-ascon       Build NEORV32 CPU+UART+ASCON-CFS bitstream"
	@echo "  make firmware              Build firmware; FIRMWARE_PROFILE=auto|soft"
	@echo "  make firmware-auto         Build firmware using host-compatible toolchain probe"
	@echo "  make firmware-soft         Build freestanding RV32I/ILP32 firmware with Nix-native toolchain"
	@echo "  make prog-sram             Program the generated bitstream"
	@echo "  make upload SERIAL=/dev/... Upload benchmark EXE through NEORV32 bootloader"
	@echo "  make uart-capture [SERIAL=/dev/...] LOG=uart.log"
	@echo "  make uart-report LOG=uart.log"
	@echo "  make doctor [SERIAL=/dev/...] [NEORV32_HOME=/path]"
	@echo "  make clean                 Remove this board target's generated handoff files"
	@echo ""
	@echo "Board support targets: manifest check preflight package build-plan session gowin-handoff rtl-list memory-map"

all: package gowin-handoff firmware bitstream

tools:
	@echo "GHDL=$(GHDL)"
	@echo "YOSYS=$(YOSYS)"
	@echo "NEXTPNR=$(NEXTPNR)"
	@echo "GOWIN_PACK=$(GOWIN_PACK)"
	@echo "OPENFPGALOADER=$(OPENFPGALOADER)"
	@command -v $(GHDL) >/dev/null || (echo "$(GHDL) not found; VHDL-to-Verilog conversion will fail"; exit 2)
	@command -v $(YOSYS) >/dev/null || (echo "$(YOSYS) not found; synthesis will fail"; exit 2)
	@command -v $(NEXTPNR) >/dev/null || (echo "$(NEXTPNR) not found; place-and-route will fail"; exit 2)
	@command -v $(GOWIN_PACK) >/dev/null || (echo "$(GOWIN_PACK) not found; bitstream packing will fail"; exit 2)
	@command -v $(OPENFPGALOADER) >/dev/null || (echo "$(OPENFPGALOADER) not found; programming targets will fail"; exit 2)
	@command -v picocom >/dev/null || (echo "picocom not found; UART capture targets will fail"; exit 2)
	@command -v $(RISCV_PREFIX)gcc >/dev/null || (echo "$(RISCV_PREFIX)gcc not found; enter nix develop or set RISCV_PREFIX=riscv32-none-elf-"; exit 2)
	@command -v $(RISCV_PREFIX)objcopy >/dev/null || (echo "$(RISCV_PREFIX)objcopy not found"; exit 2)
	@command -v $(RISCV_PREFIX)readelf >/dev/null || (echo "$(RISCV_PREFIX)readelf not found"; exit 2)
	@command -v $(RISCV_PREFIX)size >/dev/null || (echo "$(RISCV_PREFIX)size not found"; exit 2)
	@cd $(REPO_ROOT) && PYTHONPATH=. python tools/check_neorv32_toolchain.py --prefix $(RISCV_PREFIX) --profile $(NEORV32_FW_PROFILE) --check >/dev/null
	@echo "board tools ok"

deps:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --fetch --check

manifest:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/print_neorv32_stream_board_manifest.py --json

check:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/print_neorv32_stream_board_manifest.py --check

preflight:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/neorv32_stream_board_preflight.py --check
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/neorv32_stream_board_preflight.py --out build/neorv32_stream_axis_mmio/preflight.json

package:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/prepare_neorv32_stream_board_build.py --out build/neorv32_stream_axis_mmio/package --clean
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/prepare_neorv32_stream_board_build.py --check --out build/neorv32_stream_axis_mmio/package

build-plan:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/plan_neorv32_stream_board_build.py --ensure-package --write-defaults --check
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/plan_neorv32_stream_board_build.py --json --out build/neorv32_stream_axis_mmio/build_plan.json
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/plan_neorv32_stream_board_build.py --markdown --out build/neorv32_stream_axis_mmio/build_plan.md

session:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/run_neorv32_stream_board_session.py --ensure-package --write-defaults $(if $(BITSTREAM),--bitstream $(BITSTREAM),) $(if $(LOG),--uart-log $(LOG) --strict-uart,) --check
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/run_neorv32_stream_board_session.py --json --out build/neorv32_stream_axis_mmio/session/session.json $(if $(BITSTREAM),--bitstream $(BITSTREAM),) $(if $(LOG),--uart-log $(LOG) --strict-uart,)
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/run_neorv32_stream_board_session.py --markdown --out build/neorv32_stream_axis_mmio/session/session.md $(if $(BITSTREAM),--bitstream $(BITSTREAM),) $(if $(LOG),--uart-log $(LOG) --strict-uart,)

gowin-handoff:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/prepare_neorv32_stream_gowin_handoff.py --ensure-package --out build/neorv32_stream_axis_mmio/gowin_handoff --clean
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/prepare_neorv32_stream_gowin_handoff.py --check --out build/neorv32_stream_axis_mmio/gowin_handoff

firmware:
	@if [ "$(FIRMWARE_PROFILE)" = "soft" ]; then \
	  $(MAKE) firmware-soft; \
	else \
	  $(MAKE) firmware-auto; \
	fi

firmware-auto:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --fetch --check
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/check_neorv32_toolchain.py --prefix $(RISCV_PREFIX) --profile $(NEORV32_FW_PROFILE) --check
	cd $(REPO_ROOT) && NEORV32_RESOLVED="$$(PYTHONPATH=. python tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --print-home)"; \
	TOOLCHAIN_ARGS="$$(PYTHONPATH=. python tools/check_neorv32_toolchain.py --prefix $(RISCV_PREFIX) --profile $(NEORV32_FW_PROFILE) --make-args)"; \
	$(MAKE) -C firmware/neorv32_ascon_benchmark NEORV32_HOME="$$NEORV32_RESOLVED" RISCV_PREFIX=$(RISCV_PREFIX) $$TOOLCHAIN_ARGS USE_CFS_AXIS_MMIO=1 clean_all exe

firmware-soft:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --fetch --check
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/check_neorv32_toolchain.py --prefix $(RISCV_PREFIX) --profile freestanding-soft --check
	cd $(REPO_ROOT) && NEORV32_RESOLVED="$$(PYTHONPATH=. python tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --print-home)"; \
	$(MAKE) -C firmware/neorv32_ascon_benchmark NEORV32_HOME="$$NEORV32_RESOLVED" RISCV_PREFIX=$(RISCV_PREFIX) MARCH=rv32i_zicsr_zifencei MABI=ilp32 USE_CFS_AXIS_MMIO=1 FREESTANDING=1 LD_LIBS= USER_LIBS= clean_all exe

firmware-image-soft:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --fetch --check
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/check_neorv32_toolchain.py --prefix $(RISCV_PREFIX) --profile freestanding-soft --check
	cd $(REPO_ROOT) && NEORV32_RESOLVED="$$(PYTHONPATH=. python tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --print-home)"; \
	$(MAKE) -C firmware/neorv32_ascon_benchmark NEORV32_HOME="$$NEORV32_RESOLVED" RISCV_PREFIX=$(RISCV_PREFIX) MARCH=rv32i_zicsr_zifencei MABI=ilp32 USE_CFS_AXIS_MMIO=1 FREESTANDING=1 LD_LIBS= USER_LIBS= clean_all image

bitstream-plain:
	$(MAKE) TOP_MODE=plain bitstream

bitstream-ascon:
	$(MAKE) TOP_MODE=ascon bitstream

bitstream: package gowin-handoff $(FS)
	@echo "wrote $(FS)"

$(BOARD_BUILD):
	mkdir -p $(BOARD_BUILD)/ghdl

$(VHDL_NETLIST): $(VHDL_SRCS) | $(BOARD_BUILD)
	@echo "Converting NEORV32 VHDL to Verilog: TOP_MODE=$(TOP_MODE) TOP=$(TOP)"
	$(GHDL) -i --std=08 --work=neorv32 --workdir=$(BOARD_BUILD)/ghdl -P$(BOARD_BUILD)/ghdl $(VHDL_SRCS)
	$(GHDL) -m --std=08 --work=neorv32 --workdir=$(BOARD_BUILD)/ghdl -P$(BOARD_BUILD)/ghdl $(TOP)
	$(GHDL) synth --std=08 --work=neorv32 --workdir=$(BOARD_BUILD)/ghdl -P$(BOARD_BUILD)/ghdl --out=verilog $(TOP) > $(VHDL_NETLIST)

$(JSON): $(VHDL_NETLIST) $(ASCON_VERILOG_SRCS) | $(BOARD_BUILD)
	$(YOSYS) -q -p "read_verilog -I$(REPO_ROOT)/rtl/common -I$(REPO_ROOT)/rtl/stream $(ASCON_VERILOG_SRCS) $(VHDL_NETLIST); synth_gowin -top $(TOP) -json $(JSON)"

$(PNR_JSON): $(JSON) $(CST)
	@if [ "$$(basename "$(NEXTPNR)")" = "nextpnr-gowin" ]; then \
	  $(NEXTPNR) --json $(JSON) --write $(PNR_JSON) --freq 27 --device $(DEVICE) --family $(FAMILY) --cst $(CST); \
	else \
	  $(NEXTPNR) --json $(JSON) --write $(PNR_JSON) --freq 27 --device $(DEVICE) --vopt family=$(FAMILY) --vopt cst=$(CST); \
	fi

$(FS): $(PNR_JSON)
	$(GOWIN_PACK) -d $(FAMILY) -o $(FS) $(PNR_JSON)

upload: firmware-soft
	@test -n "$(SERIAL)" || (echo "Set SERIAL=/dev/serial/by-id/... or SERIAL=/dev/ttyUSBx"; exit 2)
	cd $(REPO_ROOT) && NEORV32_RESOLVED="$$(PYTHONPATH=. python tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --print-home)"; \
	$(MAKE) -C firmware/neorv32_ascon_benchmark NEORV32_HOME="$$NEORV32_RESOLVED" RISCV_PREFIX=$(RISCV_PREFIX) MARCH=rv32i_zicsr_zifencei MABI=ilp32 USE_CFS_AXIS_MMIO=1 FREESTANDING=1 LD_LIBS= USER_LIBS= UART_TTY=$(SERIAL) upload

uart-report:
	@test -n "$(LOG)" || (echo "Set LOG=/path/to/neorv32_uart.log"; exit 1)
	@test -s "$(LOG)" || (echo "UART log is missing or empty: $(LOG). Capture a real board log first."; exit 2)
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/parse_neorv32_ascon_uart_log.py "$(abspath $(LOG))" --strict --markdown --out build/neorv32_stream_axis_mmio/uart_report.md
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/parse_neorv32_ascon_uart_log.py "$(abspath $(LOG))" --strict --json --out build/neorv32_stream_axis_mmio/uart_report.json

uart-capture:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/capture_neorv32_uart.py $(SERIAL_ARG) --baud $(BAUD) --log "$(abspath $(LOG))"

doctor:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/neorv32_stream_bringup_doctor.py $(NEORV32_ARG) $(SERIAL_ARG) --write-defaults

prog-sram:
	@test -s "$(BITSTREAM)" || (echo "Bitstream not found: $(BITSTREAM). Run make bitstream-ascon or set BITSTREAM=/path/to/neorv32.fs."; exit 2)
	$(OPENFPGALOADER) -b $(BOARD) "$(BITSTREAM)"

prog-flash:
	@test -s "$(BITSTREAM)" || (echo "Bitstream not found: $(BITSTREAM). Run make bitstream-ascon or set BITSTREAM=/path/to/neorv32.fs."; exit 2)
	$(OPENFPGALOADER) -b $(BOARD) -f "$(BITSTREAM)"

rtl-list:
	@cat $(REPO_ROOT)/rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f

memory-map:
	@echo "ASCON_ACCEL_BASE_ADDR=0xFFEB0000u"
	@echo "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR=0xFFEB0100u"

clean:
	cd $(REPO_ROOT) && rm -rf build/neorv32_stream_axis_mmio
	cd $(REPO_ROOT) && $(MAKE) -C firmware/neorv32_ascon_benchmark clean_all >/dev/null 2>&1 || true
