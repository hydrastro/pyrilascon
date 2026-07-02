SHELL := /bin/sh
PYTHON ?= python
PYTEST ?= pytest
PYTEST_FLAGS ?= -q
ENGINE_COUNT ?= 4
PIPELINE_COUNT ?= 2
CONTEXTS_PER_ENGINE ?= 12
CONTEXTS_PER_PIPELINE ?= $(CONTEXTS_PER_ENGINE)
BUILD_DIR ?= build
ALGOS ?= requested
TN20K_DIR := boards/tangnano20k/neorv32_mmio
SERIAL ?=

ENV := PYTHONPATH=.
PY := $(ENV) $(PYTHON)
PYTEST_CMD := $(ENV) $(PYTEST)

.PHONY: help env check-layout test test-all test-kat test-spec test-arch \
        generate-verilog list-configs list-configs-csv list-configs-json docs-configs \
        stream-encrypt-sim stream-decrypt-sim axis-mmio-bridge-sim stream-axis-mmio-system-sim stream-axis-dma-system-sim stream-axis-dma-system-sweep firmware-stream-ref-bench project-status-report project-checkpoint-bundle matrix design-asic design-fpga design-fpga-pipeline design-fpga-mpipelines \
        clean clean-cache clean-generated clean-build clean-nested repair verify all
.PHONY: sanity repo-audit clean-repo-junk clean-board distclean \
        tn20k-doctor tn20k-sanity tn20k-firmware tn20k-bitstream tn20k-rebuild \
        tn20k-detect tn20k-prog-sram tn20k-prog-flash tn20k-capture tn20k-report tn20k-benchmark


help:
	@echo "ASCON repo targets"
	@echo ""
	@echo "  make sanity                Repository hygiene audit + complete pytest suite"
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
	@echo "  make stream-axis-dma-system-sim Run optional Icarus cosim for the autonomous descriptor-driven DMA front-end"
	@echo "  make stream-axis-dma-system-sweep Run the DMA front-end per-payload sweep (RASD 8.4 sizes: 64/256/1024 B)"
	@echo "  make firmware-stream-ref-bench Run host firmware benchmark through the AXI-stream reference emulator"
	@echo "  make tn20k-doctor          Check the Tang Nano 20K toolchain and dependencies"
	@echo "  make tn20k-bitstream       Rebuild firmware and the Tang Nano 20K bitstream"
	@echo "  make tn20k-prog-sram       Load the current target into volatile SRAM"
	@echo "  make tn20k-capture SERIAL=...   Capture a complete UART benchmark run"
	@echo "  make tn20k-report          Validate the capture and generate result tables"
	@echo "  make tn20k-prog-flash      Write the validated image to persistent flash"
	@echo "  make project-status-report            Generate current implementation/verification status report"
	@echo "  make project-checkpoint-bundle        Generate archiveable project checkpoint bundle"
	@echo "  make design-asic           Generate default ASIC design product"
	@echo "  make design-fpga           Generate default FPGA N-engine product"
	@echo "  make matrix                Generate selected ASIC/FPGA design matrix"
	@echo "  make clean                 Remove caches, build products, generated docs/RTL"
	@echo "  make clean-repo-junk       Remove known accidental nested copies/artifacts"
	@echo "  make distclean             Also remove root FPGA venv and pinned NEORV32 checkout"
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

repo-audit:
	$(PY) tools/check_repository_hygiene.py

sanity: repo-audit test

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

stream-axis-dma-system-sim: check-layout
	$(PY) tools/run_stream_axis_dma_system_vector.py --key-hex 000102030405060708090a0b0c0d0e0f --nonce-hex 101112131415161718191a1b1c1d1e1f --ad-hex aabbccddeeff --plaintext-hex 000102030405060708090a0b0c0d0e0f101112

stream-axis-dma-system-sweep: check-layout
	$(PY) tools/run_stream_axis_dma_system_sweep.py

firmware-stream-ref-bench: check-layout
	$(PY) tools/run_firmware_stream_ref_benchmark.py --json


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


# ---------------------------------------------------------------------------
# Tang Nano 20K convenience targets. The board Makefile remains the source of
# truth; these aliases keep the root-level workflow discoverable.
tn20k-doctor:
	$(MAKE) -C $(TN20K_DIR) doctor

tn20k-sanity:
	$(MAKE) -C $(TN20K_DIR) sanity

tn20k-firmware:
	$(MAKE) -C $(TN20K_DIR) firmware

tn20k-bitstream:
	$(MAKE) -C $(TN20K_DIR) bitstream

tn20k-rebuild:
	$(MAKE) -C $(TN20K_DIR) rebuild

tn20k-detect:
	$(MAKE) -C $(TN20K_DIR) detect

tn20k-prog-sram:
	$(MAKE) -C $(TN20K_DIR) prog-sram

tn20k-prog-flash:
	$(MAKE) -C $(TN20K_DIR) prog-flash

tn20k-capture:
	$(MAKE) -C $(TN20K_DIR) uart-capture $(if $(strip $(SERIAL)),SERIAL="$(SERIAL)",)

tn20k-report:
	$(MAKE) -C $(TN20K_DIR) uart-report

tn20k-benchmark:
	$(MAKE) -C $(TN20K_DIR) benchmark $(if $(strip $(SERIAL)),SERIAL="$(SERIAL)",)

clean-board:
	$(MAKE) -C $(TN20K_DIR) clean

clean-repo-junk:
	@rm -rf boards/tangnano20k/neorv32_mmio/.venv-fpga
	@rm -rf boards/tangnano20k/neorv32_mmio/external
	@rm -rf firmware/ascon_accel/ascon_arch firmware/ascon_accel/ascon_hwmodel
	@rm -rf firmware/ascon_accel/benchmarks firmware/ascon_accel/boards
	@rm -rf firmware/ascon_accel/configs firmware/ascon_accel/docs
	@rm -rf firmware/ascon_accel/firmware firmware/ascon_accel/rtl
	@rm -rf firmware/ascon_accel/tests firmware/ascon_accel/tools firmware/ascon_accel/vectors
	@rm -f firmware/ascon_accel/.gitignore firmware/ascon_accel/Makefile
	@rm -f firmware/ascon_accel/demo_*.py firmware/ascon_accel/flake.nix
	@rm -f firmware/ascon_accel/flake.lock firmware/ascon_accel/pytest.ini
	@rm -f firmware/ascon_accel/*.gch rtl/stream/*.bak
	@rm -f ascon_accel.o main_demo.o uart.log cosim_report.md notes
	@rm -rf mnt
	@rm -f documents/*.aux documents/*.out documents/*.toc
	@rm -f boards/tangnano9k/neorv32_stream_axis_mmio/sys
	@rm -f boards/tangnano9k/neorv32_mmio/cosim/neorv32_verilog_wrapper.v
	@echo "Known accidental repository artifacts removed."

distclean: clean clean-board clean-repo-junk
	@rm -rf .venv-fpga external/neorv32 firmware/neorv32_ascon_benchmark/build
	@echo "Removed reproducible local dependencies; run 'nix develop' to restore them."
