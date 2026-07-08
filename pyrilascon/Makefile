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
PORT ?= /dev/ttyUSB0
LOG  ?= bench.log

.PHONY: bench-native bench bench-report bench-host accel-rtl soc-check soc-build
bench-native:
	$(PYTHON) -m pytest tests/test_reference_c.py -q

bench:
	$(MAKE) -C firmware/neorv32_ascon_benchmark

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
