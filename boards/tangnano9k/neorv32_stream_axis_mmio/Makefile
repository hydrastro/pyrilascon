SHELL := /bin/sh
REPO_ROOT := ../../..
MANIFEST := manifest.json
NEORV32_HOME ?=

.PHONY: help manifest check preflight package firmware rtl-list memory-map

help:
	@echo "Tang Nano 9K NEORV32 stream ASCON scaffold"
	@echo ""
	@echo "  make manifest              Print the ASCON board manifest"
	@echo "  make check                 Validate manifest paths and memory map"
	@echo "  make preflight             Generate/check the board preflight plan"
	@echo "  make package               Generate the board build handoff package"
	@echo "  make firmware NEORV32_HOME=/path/to/neorv32"
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

firmware:
	@test -n "$(NEORV32_HOME)" || (echo "Set NEORV32_HOME=/path/to/neorv32"; exit 1)
	$(MAKE) -C $(REPO_ROOT)/firmware/neorv32_ascon_benchmark NEORV32_HOME=$(NEORV32_HOME) USE_CFS_AXIS_MMIO=1 clean_all exe

rtl-list:
	@cat $(REPO_ROOT)/rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f

memory-map:
	@echo "ASCON_ACCEL_BASE_ADDR=0xFFEB0000u"
	@echo "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR=0xFFEB0100u"
