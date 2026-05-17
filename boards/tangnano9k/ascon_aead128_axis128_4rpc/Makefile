TOP      := tangnano9k_ascon_aead128_axis128_4rpc_top
DEVICE   := GW1NR-LV9QN88PC6/I5
FAMILY   := GW1N-9C
BOARD    := tangnano9k
CST      := tangnano9k_ascon_aead128_axis128_4rpc.cst
BUILD    := build

YOSYS           ?= $(shell command -v yowasp-yosys 2>/dev/null || command -v yosys 2>/dev/null || echo yosys)
NEXTPNR         ?= $(shell command -v nextpnr-gowin 2>/dev/null || command -v yowasp-nextpnr-himbaechel-gowin 2>/dev/null || command -v nextpnr-himbaechel 2>/dev/null || echo nextpnr-himbaechel)
GOWIN_PACK      ?= gowin_pack
OPENFPGALOADER  ?= openFPGALoader

COMMON_RTL := ../../../rtl/common
SOURCES := \
  $(COMMON_RTL)/ascon_accel_regs.vh \
  $(COMMON_RTL)/ascon_accel_axis_defs.vh \
  $(COMMON_RTL)/ascon_round_comb.v \
  $(COMMON_RTL)/ascon_round4_comb.v \
  $(COMMON_RTL)/ascon_aead128_mmio_backend_4rpc.v \
  $(COMMON_RTL)/ascon_accel_mmio_regs.v \
  $(COMMON_RTL)/ascon_accel_axis128_aead128_4rpc_top.v \
  rtl/$(TOP).v

JSON := $(BUILD)/$(TOP).json
PNR_JSON := $(BUILD)/$(TOP)_pnr.json
FS := $(BUILD)/$(TOP).fs

.PHONY: all clean tools prog-sram prog-flash

all: $(FS)

tools:
	@echo "YOSYS=$(YOSYS)"
	@echo "NEXTPNR=$(NEXTPNR)"
	@echo "GOWIN_PACK=$(GOWIN_PACK)"
	@echo "OPENFPGALOADER=$(OPENFPGALOADER)"
	@which $(YOSYS)
	@which $(NEXTPNR)
	@which $(GOWIN_PACK)
	@which $(OPENFPGALOADER)

$(BUILD):
	mkdir -p $(BUILD)

$(JSON): $(SOURCES) | $(BUILD)
	$(YOSYS) -q -p "read_verilog -I$(COMMON_RTL) $(SOURCES); synth_gowin -top $(TOP) -json $(JSON)"

$(PNR_JSON): $(JSON) $(CST)
	@if [ "$$(basename "$(NEXTPNR)")" = "nextpnr-gowin" ]; then \
	  $(NEXTPNR) --json $(JSON) --write $(PNR_JSON) --freq 27 --device $(DEVICE) --family $(FAMILY) --cst $(CST); \
	else \
	  $(NEXTPNR) --json $(JSON) --write $(PNR_JSON) --freq 27 --device $(DEVICE) --vopt family=$(FAMILY) --vopt cst=$(CST); \
	fi

$(FS): $(PNR_JSON)
	$(GOWIN_PACK) -d $(FAMILY) -o $(FS) $(PNR_JSON)

prog-sram: $(FS)
	$(OPENFPGALOADER) -b $(BOARD) $(FS)

prog-flash: $(FS)
	$(OPENFPGALOADER) -b $(BOARD) -f $(FS)

clean:
	rm -rf $(BUILD)
