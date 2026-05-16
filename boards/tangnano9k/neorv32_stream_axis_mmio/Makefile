SHELL := /bin/sh
REPO_ROOT := ../../..
MANIFEST := manifest.json
BUILD := build
LOG ?= uart.log
BAUD ?= 19200
SERIAL ?=
BITSTREAM ?= $(BUILD)/neorv32_stream_axis_mmio.fs
NEORV32_DIR ?= external/neorv32
RISCV_PREFIX ?= riscv-none-elf-
NEORV32_FW_PROFILE ?= auto
FIRMWARE_PROFILE ?= auto
.DEFAULT_GOAL := all

NEORV32_ARG = $(if $(filter command line,$(origin NEORV32_HOME)),--neorv32-home $(NEORV32_HOME),)
SERIAL_ARG = $(if $(SERIAL),--serial-device $(SERIAL),)

.PHONY: help all clean tools deps manifest check preflight package build-plan session gowin-handoff \
        firmware firmware-auto firmware-soft uart-report uart-capture doctor rtl-list memory-map prog-sram prog-flash

help:
	@echo "Tang Nano 9K NEORV32 stream ASCON board target"
	@echo ""
	@echo "Workflow:"
	@echo "  make clean && make tools && make && make prog-sram"
	@echo ""
	@echo "Targets:"
	@echo "  make tools                 Check host tools used by this board target"
	@echo "  make deps                  Fetch/check the project-local NEORV32 checkout"
	@echo "  make                       Generate package/handoff and build firmware ($(FIRMWARE_PROFILE))"
	@echo "  make firmware              Build firmware; FIRMWARE_PROFILE=auto|soft"
	@echo "  make firmware-auto         Build firmware using host-compatible toolchain probe"
	@echo "  make firmware-soft         Build freestanding RV32I/ILP32 firmware with Nix-native toolchain"
	@echo "  make prog-sram BITSTREAM=... Program an existing Tang Nano 9K bitstream"
	@echo "  make uart-capture [SERIAL=/dev/...] LOG=uart.log"
	@echo "  make uart-report LOG=uart.log"
	@echo "  make doctor [SERIAL=/dev/...] [NEORV32_HOME=/path]"
	@echo "  make clean                 Remove this board target's generated handoff files"
	@echo ""
	@echo "Board support targets: manifest check preflight package build-plan session gowin-handoff rtl-list memory-map"

all: package gowin-handoff firmware

tools:
	@command -v $(RISCV_PREFIX)gcc >/dev/null || (echo "$(RISCV_PREFIX)gcc not found; enter nix develop or install a RISC-V bare-metal toolchain"; exit 2)
	@command -v $(RISCV_PREFIX)objcopy >/dev/null || (echo "$(RISCV_PREFIX)objcopy not found"; exit 2)
	@command -v $(RISCV_PREFIX)readelf >/dev/null || (echo "$(RISCV_PREFIX)readelf not found"; exit 2)
	@command -v $(RISCV_PREFIX)size >/dev/null || (echo "$(RISCV_PREFIX)size not found"; exit 2)
	@command -v openFPGALoader >/dev/null || (echo "openFPGALoader not found; programming targets will fail"; exit 2)
	@command -v picocom >/dev/null || (echo "picocom not found; UART capture targets will fail"; exit 2)
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
	@test -s "$(BITSTREAM)" || (echo "Bitstream not found: $(BITSTREAM). Set BITSTREAM=/path/to/neorv32.fs after building the full NEORV32 Tang Nano project."; exit 2)
	openFPGALoader -b tangnano9k "$(BITSTREAM)"

prog-flash:
	@test -s "$(BITSTREAM)" || (echo "Bitstream not found: $(BITSTREAM). Set BITSTREAM=/path/to/neorv32.fs after building the full NEORV32 Tang Nano project."; exit 2)
	openFPGALoader -b tangnano9k -f "$(BITSTREAM)"

rtl-list:
	@cat $(REPO_ROOT)/rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f

memory-map:
	@echo "ASCON_ACCEL_BASE_ADDR=0xFFEB0000u"
	@echo "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR=0xFFEB0100u"

clean:
	cd $(REPO_ROOT) && rm -rf build/neorv32_stream_axis_mmio
	cd $(REPO_ROOT) && $(MAKE) -C firmware/neorv32_ascon_benchmark clean_all >/dev/null 2>&1 || true
