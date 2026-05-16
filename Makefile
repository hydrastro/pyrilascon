SHELL := /bin/sh
PYTHON ?= python
PYTEST ?= pytest
PYTEST_FLAGS ?= -q
ENGINE_COUNT ?= 4
NEORV32_ARG = $(if $(filter command line,$(origin NEORV32_HOME)),--neorv32-home $(NEORV32_HOME),)
PIPELINE_COUNT ?= 2
CONTEXTS_PER_ENGINE ?= 12
CONTEXTS_PER_PIPELINE ?= $(CONTEXTS_PER_ENGINE)
BUILD_DIR ?= build
ALGOS ?= requested
LOG ?= uart.log
BAUD ?= 19200
NEORV32_DIR ?= external/neorv32
NEORV32_FW_PROFILE ?= auto
RISCV_PREFIX ?= riscv-none-elf-
NEORV32_SOFT_TOOLCHAIN_DIR ?= external/riscv32-unknown-elf-gcc-rv32i-ilp32

ENV := PYTHONPATH=.
PY := $(ENV) $(PYTHON)
PYTEST_CMD := $(ENV) $(PYTEST)

.PHONY: help env check-layout test test-all test-kat test-spec test-arch \
        generate-verilog list-configs list-configs-csv list-configs-json docs-configs \
        stream-encrypt-sim stream-decrypt-sim axis-mmio-bridge-sim stream-axis-mmio-system-sim firmware-stream-ref-bench neorv32-fetch neorv32-home neorv32-soft-toolchain-fetch neorv32-soft-toolchain-prefix neorv32-toolchain-check neorv32-stream-build-firmware neorv32-stream-build-firmware-soft neorv32-stream-uart-report neorv32-stream-uart-capture neorv32-stream-bringup-doctor neorv32-stream-board-manifest neorv32-stream-board-preflight neorv32-stream-board-package neorv32-stream-board-build-plan neorv32-stream-board-session neorv32-stream-gowin-handoff project-status-report project-checkpoint-bundle matrix design-asic design-fpga design-fpga-pipeline design-fpga-mpipelines \
        clean clean-cache clean-generated clean-build clean-nested repair verify all

help:
	@echo "ASCON repo targets"
	@echo ""
	@echo "  make test                  Run root tests only: pytest tests"
	@echo "  make test-kat              Run known-answer tests only"
	@echo "  make test-spec             Run spec/model tests"
	@echo "  make test-arch             Run architecture/config tests"
	@echo "  make generate-verilog      Regenerate rtl/generated/*.v[h]"
	@echo "  make list-configs          Print selected valid configs"
	@echo "  make docs-configs          Write config reports under docs/generated/"
	@echo "  make stream-encrypt-sim    Run one optional Icarus RTL sim vector for the stream encrypt backend"
	@echo "  make stream-decrypt-sim    Run optional valid/corrupt-tag Icarus RTL sim vectors for buffered decrypt"
	@echo "  make axis-mmio-bridge-sim Run optional Icarus sim for the CPU-driven AXI-stream MMIO bridge"
	@echo "  make stream-axis-mmio-system-sim Run optional Icarus smoke sim for the full CSR+bridge+stream AEAD system"
	@echo "  make firmware-stream-ref-bench Run host firmware benchmark through the AXI-stream reference emulator"
	@echo "  make neorv32-stream-uart-report LOG=uart.log Parse a board UART benchmark log"
	@echo "  make neorv32-stream-uart-capture SERIAL=/dev/ttyUSB0 LOG=uart.log Capture UART output with picocom"
	@echo "  make neorv32-stream-bringup-doctor SERIAL=/dev/ttyUSB0 Check NEORV32_HOME, serial permissions, and handoff files"
	@echo "  make neorv32-fetch                    Clone NEORV32 into external/neorv32 if missing"
	@echo "  make neorv32-home                     Print resolved NEORV32 checkout path"
	@echo "  make neorv32-toolchain-check          Probe RISC-V GCC ABI compatibility"
	@echo "  make neorv32-soft-toolchain-fetch     Fetch project-local RV32I/ILP32 NEORV32 GCC"
	@echo "  make neorv32-stream-build-firmware    Build NEORV32 firmware using resolved project-local checkout"
	@echo "  make neorv32-stream-build-firmware-soft Build board-safe firmware with RV32I/ILP32 soft-float toolchain"
	@echo "  make neorv32-stream-board-manifest Print/check the Tang Nano 9K NEORV32 stream manifest"
	@echo "  make neorv32-stream-board-preflight Generate/check the Tang Nano 9K NEORV32 stream board preflight plan"
	@echo "  make neorv32-stream-board-package   Generate the Tang Nano 9K NEORV32 stream board build handoff package"
	@echo "  make neorv32-stream-board-build-plan Dry-run/check the board build handoff package"
	@echo "  make neorv32-stream-board-session    Generate a board programming/UART session report"
	@echo "  make neorv32-stream-gowin-handoff    Generate the Tang Nano 9K Gowin/NEORV32 handoff"
	@echo "  make project-status-report            Generate current implementation/verification status report"
	@echo "  make project-checkpoint-bundle        Generate archiveable project checkpoint bundle"
	@echo "  make design-asic           Generate default ASIC design product"
	@echo "  make design-fpga           Generate default FPGA N-engine product"
	@echo "  make matrix                Generate selected ASIC/FPGA design matrix"
	@echo "  make clean                 Remove caches, build products, generated docs/RTL"
	@echo "  make clean-nested          Remove known nested old repo folders/zips"
	@echo "  make repair                clean-nested + clean + test"
	@echo "  make verify                Run tests, docs-configs, and Verilog generation"
	@echo ""
	@echo "Variables: PYTHON, PYTEST, PYTEST_FLAGS, ENGINE_COUNT, PIPELINE_COUNT, CONTEXTS_PER_ENGINE, BUILD_DIR, ALGOS"
	@echo "Example: make list-configs ALGOS=aead128,hash256,xof128,cxof128"

env:
	@$(PYTHON) --version
	@$(PYTEST_CMD) --version

check-layout:
	@test -d ascon_hwmodel || (echo "Missing ascon_hwmodel/. Run from repo root."; exit 1)
	@test -d tests || (echo "Missing tests/. Run from repo root."; exit 1)
	@if [ -d ignore ]; then echo "Warning: ignore/ exists. It is ignored by pytest.ini; run 'make clean-nested' to delete it."; fi
	@if [ -d ascon_hwmodel_aead_hash_step ]; then echo "Warning: nested ascon_hwmodel_aead_hash_step/ exists; run 'make clean-nested' to delete it."; fi

test: check-layout clean-cache
	$(PYTEST_CMD) $(PYTEST_FLAGS) tests

test-all: test

test-kat: check-layout clean-cache
	$(PYTEST_CMD) $(PYTEST_FLAGS) tests/test_known_answer_vectors.py

test-spec: check-layout clean-cache
	$(PYTEST_CMD) $(PYTEST_FLAGS) \
		tests/test_iv.py \
		tests/test_state.py \
		tests/test_auxiliary.py \
		tests/test_permutation.py \
		tests/test_sbox_views.py \
		tests/test_word_absorb_keyops.py \
		tests/test_aead_phases.py \
		tests/test_hash_xof.py \
		tests/test_known_answer_vectors.py

test-arch: check-layout clean-cache
	$(PYTEST_CMD) $(PYTEST_FLAGS) tests/test_arch_config.py tests/test_example_configs_validate.py tests/test_valid_config_listing.py tests/test_control_profiles.py tests/test_padding_profiles.py tests/test_security_profiles.py tests/test_top_level_profiles.py

generate-verilog: check-layout
	$(PY) tools/generate_verilog.py

list-configs: check-layout
	$(PY) tools/list_valid_configs.py --target both --algorithms $(ALGOS) --engine-count $(ENGINE_COUNT) --pipeline-count $(PIPELINE_COUNT) --contexts-per-pipeline $(CONTEXTS_PER_PIPELINE)

list-configs-csv: check-layout
	@mkdir -p docs/generated
	$(PY) tools/list_valid_configs.py --target both --algorithms $(ALGOS) --format csv --out docs/generated/selected_valid_configs.csv --engine-count $(ENGINE_COUNT) --pipeline-count $(PIPELINE_COUNT) --contexts-per-pipeline $(CONTEXTS_PER_PIPELINE)

list-configs-json: check-layout
	@mkdir -p docs/generated
	$(PY) tools/list_valid_configs.py --target both --algorithms $(ALGOS) --include-invalid --format json --out docs/generated/selected_config_validation_report.json --engine-count $(ENGINE_COUNT) --pipeline-count $(PIPELINE_COUNT) --contexts-per-pipeline $(CONTEXTS_PER_PIPELINE)

docs-configs: list-configs-csv list-configs-json
	$(PY) tools/list_valid_configs.py --target both --algorithms $(ALGOS) --format text --out docs/generated/selected_valid_configs.txt --engine-count $(ENGINE_COUNT) --pipeline-count $(PIPELINE_COUNT) --contexts-per-pipeline $(CONTEXTS_PER_PIPELINE)

stream-encrypt-sim: check-layout
	$(PY) tools/run_stream_encrypt_vector.py --key-hex 000102030405060708090a0b0c0d0e0f --nonce-hex 101112131415161718191a1b1c1d1e1f --ad-hex aabbccddeeff --plaintext-hex 000102030405060708090a0b0c0d0e0f10111208090a0b0c0d0e0f101112

stream-decrypt-sim: check-layout
	$(PY) tools/run_stream_decrypt_vector.py --key-hex 000102030405060708090a0b0c0d0e0f --nonce-hex 101112131415161718191a1b1c1d1e1f --ad-hex aabbccddeeff --plaintext-hex 000102030405060708090a0b0c0d0e0f10111208090a0b0c0d0e0f101112
	$(PY) tools/run_stream_decrypt_vector.py --corrupt-tag --key-hex 000102030405060708090a0b0c0d0e0f --nonce-hex 101112131415161718191a1b1c1d1e1f --ad-hex 6d65746164617461 --plaintext-hex 73656372657420706c61696e74657874

axis-mmio-bridge-sim: check-layout
	$(PY) tools/run_axis_mmio_bridge_vector.py --json

stream-axis-mmio-system-sim: check-layout
	$(PY) tools/run_stream_axis_mmio_system_vector.py --key-hex 000102030405060708090a0b0c0d0e0f --nonce-hex 101112131415161718191a1b1c1d1e1f --ad-hex aabbccddeeff --plaintext-hex 000102030405060708090a0b0c0d0e0f101112

firmware-stream-ref-bench: check-layout
	$(PY) tools/run_firmware_stream_ref_benchmark.py --json

neorv32-stream-uart-report: check-layout
	@test -n "$(LOG)" || (echo "Set LOG=/path/to/neorv32_uart.log"; exit 1)
	@test -s "$(LOG)" || (echo "UART log is missing or empty: $(LOG). Capture a real board log first."; exit 2)
	$(PY) tools/parse_neorv32_ascon_uart_log.py "$(LOG)" --strict --markdown --out $(BUILD_DIR)/neorv32_stream_axis_mmio/uart_report.md
	$(PY) tools/parse_neorv32_ascon_uart_log.py "$(LOG)" --strict --json --out $(BUILD_DIR)/neorv32_stream_axis_mmio/uart_report.json

neorv32-fetch: check-layout
	$(PY) tools/ensure_neorv32_checkout.py --vendor-dir $(NEORV32_DIR) --fetch --check

neorv32-home: check-layout
	$(PY) tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --print-home


neorv32-soft-toolchain-fetch: check-layout
	$(PY) tools/ensure_neorv32_soft_toolchain.py --toolchain-dir $(NEORV32_SOFT_TOOLCHAIN_DIR) --fetch --check

neorv32-soft-toolchain-prefix: check-layout
	$(PY) tools/ensure_neorv32_soft_toolchain.py --toolchain-dir $(NEORV32_SOFT_TOOLCHAIN_DIR) --print-prefix

neorv32-toolchain-check: check-layout
	$(PY) tools/check_neorv32_toolchain.py --prefix $(RISCV_PREFIX) --profile $(NEORV32_FW_PROFILE) --check

neorv32-stream-build-firmware: check-layout neorv32-toolchain-check
	NEORV32_RESOLVED="$$(PYTHONPATH=. $(PYTHON) tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --print-home)"; \
	TOOLCHAIN_ARGS="$$(PYTHONPATH=. $(PYTHON) tools/check_neorv32_toolchain.py --prefix $(RISCV_PREFIX) --profile $(NEORV32_FW_PROFILE) --make-args)"; \
	$(MAKE) -C firmware/neorv32_ascon_benchmark NEORV32_HOME="$$NEORV32_RESOLVED" RISCV_PREFIX=$(RISCV_PREFIX) $$TOOLCHAIN_ARGS USE_CFS_AXIS_MMIO=1 clean_all exe


neorv32-stream-build-firmware-soft: check-layout neorv32-soft-toolchain-fetch
	NEORV32_RESOLVED="$$(PYTHONPATH=. $(PYTHON) tools/ensure_neorv32_checkout.py $(NEORV32_ARG) --vendor-dir $(NEORV32_DIR) --print-home)"; \
	SOFT_PREFIX="$$(PYTHONPATH=. $(PYTHON) tools/ensure_neorv32_soft_toolchain.py --toolchain-dir $(NEORV32_SOFT_TOOLCHAIN_DIR) --print-prefix)"; \
	PYTHONPATH=. $(PYTHON) tools/check_neorv32_toolchain.py --prefix "$$SOFT_PREFIX" --profile soft --check; \
	$(MAKE) -C firmware/neorv32_ascon_benchmark NEORV32_HOME="$$NEORV32_RESOLVED" RISCV_PREFIX="$$SOFT_PREFIX" MARCH=rv32i_zicsr_zifencei MABI=ilp32 USE_CFS_AXIS_MMIO=1 clean_all exe

neorv32-stream-uart-capture: check-layout
	$(PY) tools/capture_neorv32_uart.py $(if $(SERIAL),--serial-device $(SERIAL),) --baud $(BAUD) --log "$(LOG)"

neorv32-stream-bringup-doctor: check-layout
	$(PY) tools/neorv32_stream_bringup_doctor.py $(NEORV32_ARG) $(if $(SERIAL),--serial-device $(SERIAL),) --write-defaults

neorv32-stream-board-manifest: check-layout
	$(PY) tools/print_neorv32_stream_board_manifest.py --check
	$(PY) tools/print_neorv32_stream_board_manifest.py

neorv32-stream-board-preflight: check-layout
	$(PY) tools/neorv32_stream_board_preflight.py --check
	$(PY) tools/neorv32_stream_board_preflight.py --out $(BUILD_DIR)/neorv32_stream_axis_mmio/preflight.json

neorv32-stream-board-package: check-layout
	$(PY) tools/prepare_neorv32_stream_board_build.py --out $(BUILD_DIR)/neorv32_stream_axis_mmio/package --clean
	$(PY) tools/prepare_neorv32_stream_board_build.py --check --out $(BUILD_DIR)/neorv32_stream_axis_mmio/package

neorv32-stream-board-build-plan: check-layout
	$(PY) tools/plan_neorv32_stream_board_build.py --ensure-package --write-defaults --check
	$(PY) tools/plan_neorv32_stream_board_build.py --json --out $(BUILD_DIR)/neorv32_stream_axis_mmio/build_plan.json
	$(PY) tools/plan_neorv32_stream_board_build.py --markdown --out $(BUILD_DIR)/neorv32_stream_axis_mmio/build_plan.md

neorv32-stream-board-session: check-layout
	$(PY) tools/run_neorv32_stream_board_session.py --ensure-package --write-defaults $(if $(BITSTREAM),--bitstream $(BITSTREAM),) $(if $(LOG),--uart-log $(LOG) --strict-uart,) --check
	$(PY) tools/run_neorv32_stream_board_session.py --json --out $(BUILD_DIR)/neorv32_stream_axis_mmio/session/session.json $(if $(BITSTREAM),--bitstream $(BITSTREAM),) $(if $(LOG),--uart-log $(LOG) --strict-uart,)
	$(PY) tools/run_neorv32_stream_board_session.py --markdown --out $(BUILD_DIR)/neorv32_stream_axis_mmio/session/session.md $(if $(BITSTREAM),--bitstream $(BITSTREAM),) $(if $(LOG),--uart-log $(LOG) --strict-uart,)

neorv32-stream-gowin-handoff: check-layout
	$(PY) tools/prepare_neorv32_stream_gowin_handoff.py --ensure-package --out $(BUILD_DIR)/neorv32_stream_axis_mmio/gowin_handoff --clean
	$(PY) tools/prepare_neorv32_stream_gowin_handoff.py --check --out $(BUILD_DIR)/neorv32_stream_axis_mmio/gowin_handoff

project-status-report: check-layout
	$(PY) tools/generate_project_status_report.py --check
	$(PY) tools/generate_project_status_report.py --write-defaults

project-checkpoint-bundle: check-layout project-status-report
	$(PY) tools/generate_project_checkpoint_bundle.py --write-defaults --clean
	$(PY) tools/generate_project_checkpoint_bundle.py --check

design-asic: check-layout
	$(PY) tools/generate_design.py --preset asic_dual_enc_dec_cores --out $(BUILD_DIR)

design-fpga: check-layout
	$(PY) tools/generate_design.py --preset fpga_n_parallel_engines --engine-count $(ENGINE_COUNT) --out $(BUILD_DIR)

design-fpga-pipeline: check-layout
	$(PY) tools/generate_design.py --preset fpga_one_pipelined_permutation_n_contexts --contexts-per-engine $(CONTEXTS_PER_ENGINE) --out $(BUILD_DIR)

design-fpga-mpipelines: check-layout
	$(PY) tools/generate_design.py --preset fpga_m_pipelines_n_contexts --engine-count $(PIPELINE_COUNT) --contexts-per-engine $(CONTEXTS_PER_PIPELINE) --out $(BUILD_DIR)

matrix: check-layout
	$(PY) tools/generate_matrix.py --target both --engine-count $(ENGINE_COUNT) --out $(BUILD_DIR)/matrix --write-invalid-report

clean-cache:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	@find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	@rm -rf .mypy_cache .ruff_cache htmlcov .coverage

clean-build:
	@rm -rf $(BUILD_DIR)

clean-generated:
	@mkdir -p rtl/generated docs/generated vectors/generated
	@find rtl/generated -type f ! -name .gitkeep -delete
	@find docs/generated -type f ! -name .gitkeep -delete
	@find vectors/generated -type f ! -name .gitkeep -delete
	@touch rtl/generated/.gitkeep docs/generated/.gitkeep vectors/generated/.gitkeep

clean-nested:
	@rm -rf ignore
	@rm -rf ascon_hwmodel_aead_hash_step
	@rm -f ascon_hwmodel_aead_hash_step.zip repo.zip

clean: clean-cache clean-build clean-generated

repair: clean-nested clean test

verify: test docs-configs generate-verilog

all: verify design-asic design-fpga design-fpga-pipeline design-fpga-mpipelines
