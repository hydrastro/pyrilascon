TOP      := tangnano9k_ascon_aead128_kat_top
DEVICE   := GW1NR-LV9QN88PC6/I5
FAMILY   := GW1N-9C
FREQ     := 27
CST      := tangnano9k_ascon_aead128_kat.cst
BUILD    := build

YOSYS           ?= yosys
NEXTPNR         ?= nextpnr-himbaechel
GOWIN_PACK      ?= gowin_pack
OPENFPGALOADER  ?= openFPGALoader

VERILOG := \
	rtl/ascon_round_comb.v \
	rtl/ascon_aead128_kat_slow_core.v \
	rtl/tangnano9k_ascon_aead128_kat_top.v

JSON     := $(BUILD)/$(TOP).json
PNR_JSON := $(BUILD)/$(TOP).pnr.json
FS       := $(BUILD)/$(TOP).fs

.PHONY: all clean prog-sram prog-flash tools

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

$(JSON): $(VERILOG) | $(BUILD)
	$(YOSYS) -q -p 'read_verilog $(VERILOG); synth_gowin -top $(TOP) -json $(JSON)'

$(PNR_JSON): $(JSON) $(CST)
	$(NEXTPNR) \
		--json $(JSON) \
		--write $(PNR_JSON) \
		--freq $(FREQ) \
		--device $(DEVICE) \
		--vopt family=$(FAMILY) \
		--vopt cst=$(CST)

$(FS): $(PNR_JSON)
	$(GOWIN_PACK) -d $(FAMILY) -o $(FS) $(PNR_JSON)

prog-sram: $(FS)
	$(OPENFPGALOADER) -b tangnano9k $(FS)

prog-flash: $(FS)
	$(OPENFPGALOADER) -b tangnano9k -f $(FS)

clean:
	rm -rf $(BUILD)
