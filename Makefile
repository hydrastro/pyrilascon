# pyrilascon - slim top-level targets.
PYTHON ?= python3

.PHONY: help test catalog clean
help:
	@echo "pyrilascon targets:"
	@echo "  nix develop       Enter a shell with the full toolchain (or: direnv allow)"
	@echo ""
	@echo "  make test         Run the golden-model + generator + catalog suite"
	@echo "  make catalog      Print the design-space catalog and tier breakdown"
	@echo "  make clean        Remove caches and build outputs"
	@echo ""
	@echo "Boards (one flow for every board):"
	@echo "  make flash BOARD=tangnano9k TARGET=perm_smoke   Synthesize+flash a target"
	@echo "  make board-dry-run BOARD=... TARGET=...          Print the exact toolchain flow"
	@echo ""
	@echo "Benchmark (same-fabric HW-vs-CPU cycles):"
	@echo "  make bench-native   Cross-check the C reference vs the golden model (runs here)"
	@echo "  make bench          Build the on-chip NEORV32 benchmark image (needs NEORV32 gcc)"
	@echo "  make bench-report LOG=run.log   Parse a captured UART log into a SW-vs-HW table"
	@echo "  make bench-host PORT=/dev/ttyUSB0 LOG=run.log   Capture the board's UART output"
	@echo ""
	@echo "Board, one command each (nothing flashes unless the name says flash):"
	@echo "  make ports              Show serial ports and the auto-detected PORT"
	@echo "  make bench-run          Build + upload the benchmark + print the SW-vs-HW table"
	@echo "  make demo-run           Build + upload the live demo (encrypt/decrypt/tamper)"
	@echo "  make soc-flash-spi      Flash the proven MMIO SoC to SPI (persistent)"
	@echo ""
	@echo "Stream (SLINK+DMA) SoC -- separate build dir, never clobbers build/soc:"
	@echo "  make soc-check-slink    Elaborate it (fast -- do this FIRST)"
	@echo "  make soc-build-slink    Build its bitstream"
	@echo "  make soc-flash-slink    Flash it to SRAM (power-cycle restores your SPI SoC)"
	@echo "  make slink-test-run     Build + upload the SLINK self-test"
	@echo "  make slink-bench-run    Build + upload the SLINK benchmark + table"
	@echo "  make slink-demo-run     Build + upload the SLINK live demo"
	@echo ""
	@echo "  NOTE: the MMIO benchmark cannot drive the stream SoC (it writes"
	@echo "        DATA_IN/DATA_IN_CTRL, which the stream SoC does not have)."

test:
	$(PYTHON) -m pytest -q

catalog:
	$(PYTHON) -m ascon_designspace

clean:
	rm -rf build dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache

# ---- boards: one flow for every board ------------------------------------
BOARD  ?= tangnano9k
TARGET ?= perm_smoke

.PHONY: boards targets board-dry-run synth flash flash-spi
boards: ; $(PYTHON) -m ascon_boards list-boards
targets: ; $(PYTHON) -m ascon_boards list-targets
board-dry-run: ; $(PYTHON) -m ascon_boards build --board $(BOARD) --target $(TARGET) --dry-run
synth: ; $(PYTHON) -m ascon_boards synth --board $(BOARD) --target $(TARGET)
flash: ; $(PYTHON) -m ascon_boards flash --board $(BOARD) --target $(TARGET)
flash-spi: ; $(PYTHON) -m ascon_boards flash --board $(BOARD) --target $(TARGET) --to-flash

# ---- benchmark: same-fabric hardware-vs-CPU cycle comparison -------------
# The headline is an on-chip NEORV32 comparison: the C reference (software) and
# the accelerator (hardware) run on one fabric/clock, and the accelerator must
# use fewer cycles. The software baseline is verified here (bench-native); the
# on-chip run happens on the softcore/board (bench + bench-host).
# The Sipeed debugger exposes two interfaces: if00 = JTAG (openFPGALoader holds
# it), if01 = UART (the bootloader/console). Always use if01.
PORT ?= $(firstword $(wildcard /dev/serial/by-id/usb-SIPEED_USB_Debugger_*-if01-port0) /dev/ttyUSB1)
LOG  ?= run.log

.PHONY: bench-native bench bench-report bench-host accel-rtl soc-check soc-build
bench-native:
	$(PYTHON) -m pytest tests/test_reference_c.py -q

bench:  ## Build the on-chip benchmark image
	$(MAKE) -C firmware/neorv32_ascon_benchmark FREESTANDING=1 exe

bench-report:
	$(PYTHON) host/ascon_bench.py report $(LOG)

bench-host:
	$(PYTHON) host/ascon_bench.py capture --port $(PORT) --out $(LOG)

accel-rtl:  ## Emit the AXI-Stream Ascon accelerator datapath RTL (rtl/generated/accel/)
	@python3 -c "from ascon_designspace.generator.axis import write_accelerator_files as w; import ascon_hwmodel.verilog as m, pathlib; m.write_verilog_files(pathlib.Path('rtl/generated')); print('\n'.join(w('rtl/generated/accel')))"

soc-check:  ## Elaborate the NEORV32+Ascon SoC against pinned NEORV32 (GHDL, fast)
	@NEORV32_HOME="$${NEORV32_HOME:?run inside nix develop}" ./rtl/soc/build_soc.sh --check-only

soc-build:  ## Full fully-open SoC build -> bitstream (GHDL+yosys+nextpnr+gowin_pack)
	@NEORV32_HOME="$${NEORV32_HOME:?run inside nix develop}" ./rtl/soc/build_soc.sh


# ---- one-command board flows ---------------------------------------------
# `make soc-build` only BUILDS; nothing here touches the board unless the target
# name says flash. Bitstreams live in separate directories per SoC variant, so a
# stream build can never clobber the one that is known to work.
SOC_FS       ?= build/soc/neorv32_ascon_soc.fs
SOC_SLINK_FS ?= build/soc-neorv32_ascon_slink_soc/neorv32_ascon_slink_soc.fs

.PHONY: soc-flash soc-flash-spi soc-check-slink soc-build-slink soc-flash-slink \
        bench-run demo demo-run ports slink-test slink-test-run slink-bench slink-bench-run slink-demo slink-demo-run

ports:  ## List candidate serial ports (use PORT=... to override)
	@ls -l /dev/serial/by-id/ 2>/dev/null || echo "no /dev/serial/by-id -- is the board plugged in?"
	@echo "selected PORT=$(PORT)"

soc-flash:  ## Flash the proven MMIO SoC to SRAM (temporary; lost on power-cycle)
	openFPGALoader -b tangnano20k $(SOC_FS)

soc-flash-spi:  ## Flash the proven MMIO SoC to SPI flash (persistent)
	openFPGALoader -b tangnano20k -f $(SOC_FS)
	@echo ""
	@echo "==================================================================="
	@echo " NOW UNPLUG AND REPLUG THE BOARD BEFORE UPLOADING FIRMWARE."
	@echo ""
	@echo " Writing SPI flash does NOT reconfigure the FPGA. The new bitstream"
	@echo " only loads at power-up. Until you power-cycle, the FPGA is still"
	@echo " running whatever was there before -- and since this SoC has only a"
	@echo " power-on reset, that old image never returns to the bootloader."
	@echo " That is why the upload just sits there waiting."
	@echo ""
	@echo " After replugging:  make bench-run"
	@echo "==================================================================="

# ---- stream (SLINK+DMA) SoC ----------------------------------------------
# Same script, different top. Builds into build/soc-neorv32_ascon_slink_soc/,
# so build/soc/ is untouched.
SLINK_ENV = SOC_TOP=neorv32_ascon_slink_soc \
            SOC_VHD=$(CURDIR)/rtl/soc/neorv32_ascon_slink_soc.vhd \
            SOC_V="$(CURDIR)/rtl/soc/ascon_aead128_slink_wb.v $(CURDIR)/rtl/soc/ascon_aead128_slink_mmio.v $(CURDIR)/rtl/soc/ascon_slink_shim.v"

soc-check-slink:  ## Elaborate the stream SoC (fast; do this BEFORE the long build)
	@NEORV32_HOME="$${NEORV32_HOME:?run inside nix develop}" $(SLINK_ENV) ./rtl/soc/build_soc.sh --check-only

soc-build-slink:  ## Build the stream SoC bitstream (separate dir; does not clobber build/soc)
	@NEORV32_HOME="$${NEORV32_HOME:?run inside nix develop}" $(SLINK_ENV) ./rtl/soc/build_soc.sh

soc-flash-slink:  ## Flash the stream SoC to SRAM only -- power-cycle restores your SPI SoC
	openFPGALoader -b tangnano20k $(SOC_SLINK_FS)

# ---- benchmark / demo: build, upload, report ------------------------------
bench-run: bench  ## Build + upload the benchmark, then print the SW-vs-HW table
	$(PYTHON) host/neorv32_upload.py $(PORT) firmware/neorv32_ascon_benchmark/neorv32_exe.bin $(LOG)
	$(PYTHON) host/ascon_bench.py report $(LOG)

demo:  ## Build the live-demo image
	$(MAKE) -C firmware/ascon_demo FREESTANDING=1 exe

demo-run: demo  ## Build + upload the live demo (encrypt, time, decrypt, tamper test)
	$(PYTHON) host/neorv32_upload.py $(PORT) firmware/ascon_demo/neorv32_exe.bin demo.log

slink-test:  ## Build the SLINK data-plane self-test image
	$(MAKE) -C firmware/ascon_slink_test FREESTANDING=1 exe

slink-test-run: slink-test  ## Build + upload the SLINK self-test (needs the stream SoC flashed)
	$(PYTHON) host/neorv32_upload.py $(PORT) firmware/ascon_slink_test/neorv32_exe.bin slink.log

slink-bench:  ## Build the SLINK benchmark (same CASE format as the MMIO one)
	$(MAKE) -C firmware/ascon_slink_bench FREESTANDING=1 exe

slink-bench-run: slink-bench  ## Build + upload the SLINK benchmark, then print the table
	$(PYTHON) host/neorv32_upload.py $(PORT) firmware/ascon_slink_bench/neorv32_exe.bin slink_bench.log
	$(PYTHON) host/ascon_bench.py report slink_bench.log

slink-demo:  ## Build the SLINK live demo
	$(MAKE) -C firmware/ascon_slink_demo FREESTANDING=1 exe

slink-demo-run: slink-demo  ## Build + upload the SLINK live demo
	$(PYTHON) host/neorv32_upload.py $(PORT) firmware/ascon_slink_demo/neorv32_exe.bin slink_demo.log
