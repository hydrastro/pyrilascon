TOP      := tangnano9k_ascon_aead128_mmio_slow_top
DEVICE   := GW1NR-LV9QN88PC6/I5
FAMILY   := GW1N-9C
BOARD    := tangnano9k
CST      := tangnano9k_ascon_aead128_mmio_slow.cst
BUILD    := build

COMMON_RTL := ../../../rtl/common
SOURCES := \
  $(COMMON_RTL)/ascon_accel_regs.vh \
  $(COMMON_RTL)/ascon_round_comb.v \
  $(COMMON_RTL)/ascon_aead128_mmio_backend.v \
  $(COMMON_RTL)/ascon_accel_mmio_regs.v \
  $(COMMON_RTL)/ascon_accel_mmio_aead128_top.v \
  rtl/$(TOP).v

JSON := $(BUILD)/$(TOP).json
PNR_JSON := $(BUILD)/$(TOP)_pnr.json
FS := $(BUILD)/$(TOP).fs

.PHONY: all clean tools prog-sram prog-flash

all: $(FS)

tools:
	@command -v yosys >/dev/null
	@command -v nextpnr-gowin >/dev/null || command -v nextpnr-himbaechel >/dev/null
	@command -v gowin_pack >/dev/null
	@command -v openFPGALoader >/dev/null

$(BUILD):
	mkdir -p $(BUILD)

$(JSON): $(SOURCES) | $(BUILD)
	yosys -q -p "read_verilog -I$(COMMON_RTL) $(SOURCES); synth_gowin -top $(TOP) -json $(JSON)"

$(PNR_JSON): $(JSON) $(CST)
	@if command -v nextpnr-gowin >/dev/null; then \
	  nextpnr-gowin --json $(JSON) --write $(PNR_JSON) --freq 27 --device $(DEVICE) --family $(FAMILY) --cst $(CST); \
	else \
	  nextpnr-himbaechel --json $(JSON) --write $(PNR_JSON) --freq 27 --device $(DEVICE) --vopt family=$(FAMILY) --vopt cst=$(CST); \
	fi

$(FS): $(PNR_JSON)
	gowin_pack -d $(FAMILY) -o $(FS) $(PNR_JSON)

prog-sram: $(FS)
	openFPGALoader -b $(BOARD) $(FS)

prog-flash: $(FS)
	openFPGALoader -b $(BOARD) -f $(FS)

clean:
	rm -rf $(BUILD)
