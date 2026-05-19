# Tang Nano 9K NEORV32 + ASCON (simple MMIO CFS) — NixOS / nix develop edition
# Drop in as boards/tangnano9k/neorv32_mmio/Makefile
#
# Assumes you ran `nix develop` in the repo root, so:
#   - yowasp-yosys, yowasp-nextpnr-himbaechel-gowin are on PATH via .venv-fpga
#   - gowin_pack, openFPGALoader, picocom are on PATH from nixpkgs
#   - riscv-none-elf-gcc is on PATH (wrapper around riscv32-none-elf-gcc from
#     nixpkgs pkgsCross.riscv32-embedded.buildPackages.gcc, which ships newlib)
#   - ghdl is in the dev shell too (add to flake.nix if missing — see notes)

REPO_ROOT := $(realpath ../../..)
TOP       := tangnano9k_neorv32_mmio_top
DEVICE    := GW1NR-LV9QN88PC6/I5
FAMILY    := GW1N-9C
FREQ      := 27
CST       := tangnano9k_neorv32_mmio.cst
BUILD     := $(REPO_ROOT)/build/neorv32_mmio
NEORV32_HOME ?= $(REPO_ROOT)/external/neorv32

# Tool resolution: native first, then yowasp WASM fallback.
GHDL     ?= ghdl
YOSYS    ?= $(shell command -v yowasp-yosys                     2>/dev/null || command -v yosys           2>/dev/null || echo yosys)
NEXTPNR  ?= $(shell command -v yowasp-nextpnr-himbaechel-gowin  2>/dev/null || command -v nextpnr-himbaechel 2>/dev/null || command -v nextpnr-gowin 2>/dev/null || echo nextpnr-himbaechel)
GOWIN_PACK ?= gowin_pack
OPENFPGALOADER ?= openFPGALoader
RISCV_PREFIX ?= riscv-none-elf-
SERIAL ?=
BAUD   ?= 19200
LOG    ?= uart_mmio.log

# Firmware toolchain probe profile: 'auto' lets check_neorv32_toolchain.py
# pick whatever combination of march/mabi the nix RISC-V cross can link.
# Override with NEORV32_FW_PROFILE=soft (or freestanding-soft) for reproducibility.
NEORV32_FW_PROFILE ?= auto

# ── ASCON RTL (MMIO-only CFS path) ──────────────────────────────────────────
ASCON_VERILOG_SRCS := \
	$(REPO_ROOT)/rtl/common/ascon_accel_regs.vh \
	$(REPO_ROOT)/rtl/common/ascon_round_comb.v \
	$(REPO_ROOT)/rtl/common/ascon_aead128_mmio_backend.v \
	$(REPO_ROOT)/rtl/common/ascon_accel_mmio_regs.v \
	$(REPO_ROOT)/rtl/common/ascon_accel_mmio_aead128_top.v

# ── NEORV32 VHDL via file_list_soc.f (the upstream-supported approach) ──────
NEORV32_RTL  := $(NEORV32_HOME)/rtl
NEORV32_FF   := $(shell cat $(NEORV32_RTL)/file_list_soc.f 2>/dev/null)
NEORV32_ALL  := $(subst NEORV32_RTL_PATH_PLACEHOLDER,$(NEORV32_RTL),$(NEORV32_FF))
# Drop the stock CFS template so our neorv32_cfs_ascon.vhd takes the entity name.
NEORV32_VHDL_SRCS := $(filter-out %/neorv32_cfs.vhd,$(NEORV32_ALL))

ASCON_CFS_VHDL  := $(REPO_ROOT)/rtl/neorv32/neorv32_cfs_ascon.vhd
BOARD_TOP_VHDL  := rtl/$(TOP).vhd
VHDL_SRCS       := $(NEORV32_VHDL_SRCS) $(ASCON_CFS_VHDL) $(BOARD_TOP_VHDL)

GHDL_DIR := $(BUILD)/ghdl
GHDL_V   := $(BUILD)/$(TOP)_ghdl.v
JSON     := $(BUILD)/$(TOP).json
PNR_JSON := $(BUILD)/$(TOP)_pnr.json
FS       := $(BUILD)/$(TOP).fs

.PHONY: all clean tools ghdl bitstream prog-sram prog-flash firmware upload uart-capture uart-report

all: bitstream firmware

$(BUILD): ; mkdir -p $(BUILD)

# ── GHDL: analyze + synth NEORV32 + ASCON CFS into one Verilog netlist ──────
ghdl: $(GHDL_V)
$(GHDL_V): $(VHDL_SRCS) | $(BUILD)
	mkdir -p $(GHDL_DIR)
	$(GHDL) -i --std=08 --work=neorv32 --workdir=$(GHDL_DIR) -P$(GHDL_DIR) $(VHDL_SRCS)
	$(GHDL) -m --std=08 --work=neorv32 --workdir=$(GHDL_DIR) -P$(GHDL_DIR) $(TOP)
	$(GHDL) synth --std=08 --work=neorv32 --workdir=$(GHDL_DIR) -P$(GHDL_DIR) --out=verilog $(TOP) > $(GHDL_V)

bitstream: $(FS)
$(JSON): $(GHDL_V) $(ASCON_VERILOG_SRCS) | $(BUILD)
	$(YOSYS) -q -p "read_verilog -I$(REPO_ROOT)/rtl/common $(ASCON_VERILOG_SRCS) $(GHDL_V); synth_gowin -top $(TOP) -json $(JSON)"

$(PNR_JSON): $(JSON) | $(BUILD)
	@if [ "$$(basename "$(NEXTPNR)")" = "nextpnr-gowin" ]; then \
	  $(NEXTPNR) --json $(JSON) --write $(PNR_JSON) --freq $(FREQ) --device $(DEVICE) --family $(FAMILY) --cst $(CURDIR)/$(CST); \
	else \
	  $(NEXTPNR) --json $(JSON) --write $(PNR_JSON) --freq $(FREQ) --device $(DEVICE) --vopt family=$(FAMILY) --vopt cst=$(CURDIR)/$(CST); \
	fi

$(FS): $(PNR_JSON) | $(BUILD)
	$(GOWIN_PACK) -d $(FAMILY) -o $(FS) $(PNR_JSON)
	@echo "Bitstream: $(FS)"

prog-sram: $(FS) ; $(OPENFPGALOADER) -b tangnano9k $(FS)
prog-flash: $(FS) ; $(OPENFPGALOADER) -b tangnano9k --write-flash $(FS)

# ── Firmware via the project's auto-probe ───────────────────────────────────
# This lets check_neorv32_toolchain.py choose whichever march/mabi nix's
# riscv-none-elf-gcc can actually link with its bundled newlib multilibs.
# On most NixOS shells this picks the 'soft' profile and works without any
# FREESTANDING workaround.
firmware:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/check_neorv32_toolchain.py \
		--prefix $(RISCV_PREFIX) --profile $(NEORV32_FW_PROFILE) --check
	cd $(REPO_ROOT) && \
	  TOOLCHAIN_ARGS="$$(PYTHONPATH=. python tools/check_neorv32_toolchain.py \
	    --prefix $(RISCV_PREFIX) --profile $(NEORV32_FW_PROFILE) --make-args)"; \
	  $(MAKE) -C firmware/neorv32_ascon_benchmark \
	    NEORV32_HOME=$(NEORV32_HOME) \
	    RISCV_PREFIX=$(RISCV_PREFIX) \
	    $$TOOLCHAIN_ARGS \
	    clean_all exe

upload: firmware
	@test -n "$(SERIAL)" || (echo "Set SERIAL=/dev/serial/by-id/usb-SIPEED_JTAG_Debugger_SIPEED-if01-port0"; exit 2)
	cd $(REPO_ROOT) && \
	  TOOLCHAIN_ARGS="$$(PYTHONPATH=. python tools/check_neorv32_toolchain.py \
	    --prefix $(RISCV_PREFIX) --profile $(NEORV32_FW_PROFILE) --make-args)"; \
	  $(MAKE) -C firmware/neorv32_ascon_benchmark \
	    NEORV32_HOME=$(NEORV32_HOME) \
	    RISCV_PREFIX=$(RISCV_PREFIX) \
	    $$TOOLCHAIN_ARGS \
	    UART_TTY=$(SERIAL) upload

uart-capture:
	@test -n "$(SERIAL)" || (echo "Set SERIAL=/dev/serial/by-id/usb-SIPEED_JTAG_Debugger_SIPEED-if01-port0"; exit 2)
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/capture_neorv32_uart.py \
		--serial-device $(SERIAL) --baud $(BAUD) --log $(CURDIR)/$(LOG)

uart-report:
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/parse_neorv32_ascon_uart_log.py \
		$(CURDIR)/$(LOG) --markdown --out $(BUILD)/uart_report.md
	cd $(REPO_ROOT) && PYTHONPATH=. python tools/parse_neorv32_ascon_uart_log.py \
		$(CURDIR)/$(LOG) --json --out $(BUILD)/uart_report.json
	@cat $(BUILD)/uart_report.md

tools:
	@echo "GHDL=$(GHDL)";                command -v $(GHDL)             >/dev/null && echo "  OK" || echo "  MISSING (add 'ghdl' to flake.nix devShell packages)"
	@echo "YOSYS=$(YOSYS)";              command -v $(YOSYS)            >/dev/null && echo "  OK" || echo "  MISSING (pip: yowasp-yosys)"
	@echo "NEXTPNR=$(NEXTPNR)";          command -v $(NEXTPNR)          >/dev/null && echo "  OK" || echo "  MISSING (pip: yowasp-nextpnr-himbaechel-gowin)"
	@echo "GOWIN_PACK=$(GOWIN_PACK)";    command -v $(GOWIN_PACK)       >/dev/null && echo "  OK" || echo "  MISSING (provided by yowasp; or 'pip install apicula')"
	@echo "OPENFPGALOADER=$(OPENFPGALOADER)"; command -v $(OPENFPGALOADER) >/dev/null && echo "  OK" || echo "  MISSING (add 'openfpgaloader' to flake)"
	@echo "RISCV gcc=$(RISCV_PREFIX)gcc"; command -v $(RISCV_PREFIX)gcc >/dev/null && echo "  OK" || echo "  MISSING (nix devShell should provide it via riscv32-none-elf-gcc + wrappers)"
	@echo "picocom"; command -v picocom >/dev/null && echo "  OK" || echo "  MISSING (add 'picocom' to flake)"
	@cd $(REPO_ROOT) && PYTHONPATH=. python tools/check_neorv32_toolchain.py --prefix $(RISCV_PREFIX) --profile $(NEORV32_FW_PROFILE) --check 2>&1 | grep -E "^selected|^errors" || true

clean:
	rm -rf $(BUILD)
