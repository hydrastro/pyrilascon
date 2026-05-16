SHELL := /bin/sh
REPO_ROOT := ../../..
MANIFEST := manifest.json
NEORV32_ARG = $(if $(filter command line,$(origin NEORV32_HOME)),--neorv32-home $(NEORV32_HOME),)
LOG ?= uart.log
BAUD ?= 19200

.PHONY: help manifest check preflight package build-plan session gowin-handoff firmware uart-report uart-capture doctor rtl-list memory-map

help:
	@echo "Tang Nano 9K NEORV32 stream ASCON scaffold"
	@echo ""
	@echo "  make manifest              Print the ASCON board manifest"
	@echo "  make check                 Validate manifest paths and memory map"
	@echo "  make preflight             Generate/check the board preflight plan"
	@echo "  make package               Generate the board build handoff package"
	@echo "  make build-plan            Generate/check the dry-run build plan"
	@echo "  make session               Generate a board programming/UART session report"
	@echo "  make gowin-handoff         Generate the Gowin/NEORV32 handoff directory"
	@echo "  make firmware              Build firmware using project-local external/neorv32 by default"
	@echo "  make uart-report LOG=/path/to/uart.log"
	@echo "  make uart-capture [SERIAL=/dev/ttyUSB0] LOG=uart.log"
	@echo "  make doctor SERIAL=/dev/ttyUSB0 [NEORV32_HOME=/explicit/checkout]"
	@echo "  make rtl-list              Print the ASCON CFS file list"
	@echo "  make memory-map            Print firmware base addresses"

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

session:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/run_neorv32_stream_board_session.py --ensure-package --write-defaults $(if $(BITSTREAM),--bitstream $(BITSTREAM),) $(if $(LOG),--uart-log $(LOG) --strict-uart,) --check
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/run_neorv32_stream_board_session.py --json --out build/neorv32_stream_axis_mmio/session/session.json $(if $(BITSTREAM),--bitstream $(BITSTREAM),) $(if $(LOG),--uart-log $(LOG) --strict-uart,)
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/run_neorv32_stream_board_session.py --markdown --out build/neorv32_stream_axis_mmio/session/session.md $(if $(BITSTREAM),--bitstream $(BITSTREAM),) $(if $(LOG),--uart-log $(LOG) --strict-uart,)

gowin-handoff:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/prepare_neorv32_stream_gowin_handoff.py --ensure-package --out build/neorv32_stream_axis_mmio/gowin_handoff --clean
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/prepare_neorv32_stream_gowin_handoff.py --check --out build/neorv32_stream_axis_mmio/gowin_handoff

firmware:
	cd $(REPO_ROOT) && command -v riscv-none-elf-gcc >/dev/null 2>&1 || (echo "riscv-none-elf-gcc not found. Enter nix develop with the updated flake or install a compatible RISC-V bare-metal GCC toolchain."; exit 2)
	cd $(REPO_ROOT) && NEORV32_RESOLVED="$$(PYTHONPATH=. python tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --print-home)"; \
	$(MAKE) -C firmware/neorv32_ascon_benchmark NEORV32_HOME="$$NEORV32_RESOLVED" USE_CFS_AXIS_MMIO=1 clean_all exe

uart-report:
	@test -n "$(LOG)" || (echo "Set LOG=/path/to/neorv32_uart.log"; exit 1)
	@test -s "$(LOG)" || (echo "UART log is missing or empty: $(LOG). Capture a real board log first."; exit 2)
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/parse_neorv32_ascon_uart_log.py "$(LOG)" --strict --markdown --out build/neorv32_stream_axis_mmio/uart_report.md
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/parse_neorv32_ascon_uart_log.py "$(LOG)" --strict --json --out build/neorv32_stream_axis_mmio/uart_report.json

uart-capture:
	cd $(REPO_ROOT) && $(MAKE) neorv32-stream-uart-capture $(if $(SERIAL),SERIAL="$(SERIAL)",) LOG="$(LOG)" BAUD="$(BAUD)"

doctor:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/neorv32_stream_bringup_doctor.py $(NEORV32_ARG) $(if $(SERIAL),--serial-device $(SERIAL),) --write-defaults

rtl-list:
	@cat $(REPO_ROOT)/rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f

memory-map:
	@echo "ASCON_ACCEL_BASE_ADDR=0xFFEB0000u"
	@echo "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR=0xFFEB0100u"
