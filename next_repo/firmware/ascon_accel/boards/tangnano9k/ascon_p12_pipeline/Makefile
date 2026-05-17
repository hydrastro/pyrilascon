# Tang Nano 9K high-throughput Ascon-p[12] pipeline smoke test.
# Requires: yosys, nextpnr-gowin, gowin_pack, openFPGALoader.

TOP      := tangnano9k_ascon_p12_pipeline_top
DEVICE   := GW1NR-LV9QN88PC6/I5
FAMILY   := GW1N-9C
BOARD    := tangnano9k
CST      := tangnano9k_ascon_p12_pipeline.cst
BUILD    := build

RTL := \
  rtl/ascon_round_comb.v \
  rtl/ascon_p12_pipeline.v \
  rtl/tangnano9k_ascon_p12_pipeline_top.v

.PHONY: all clean prog-sram prog-flash

all: $(BUILD)/$(TOP).fs

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/$(TOP).json: $(RTL) | $(BUILD)
	yosys -q -p "read_verilog $(RTL); synth_gowin -top $(TOP) -json $@"

$(BUILD)/$(TOP).pnr.json: $(BUILD)/$(TOP).json $(CST)
	nextpnr-gowin --json $(BUILD)/$(TOP).json --write $@ --freq 27 --device $(DEVICE) --family $(FAMILY) --cst $(CST)

$(BUILD)/$(TOP).fs: $(BUILD)/$(TOP).pnr.json
	gowin_pack -d $(FAMILY) -o $@ $<

prog-sram: $(BUILD)/$(TOP).fs
	openFPGALoader -b $(BOARD) $<

prog-flash: $(BUILD)/$(TOP).fs
	openFPGALoader -b $(BOARD) -f $<

clean:
	rm -rf $(BUILD)
