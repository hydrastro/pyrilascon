SHELL := /bin/bash
PYTHON ?= python
export PYTHONPATH := .
PYTEST_FLAGS ?= -q
ENGINE_COUNT ?= 4
PIPELINE_COUNT ?= 2
CONTEXTS_PER_ENGINE ?= 12
CONTEXTS_PER_PIPELINE ?= $(CONTEXTS_PER_ENGINE)
BUILD_DIR ?= build

.PHONY: help env check-layout test test-all test-kat test-spec test-arch \
        generate-verilog list-configs docs-configs matrix \
        design-asic design-fpga design-fpga-pipeline design-fpga-mpipelines \
        clean clean-cache clean-generated clean-build clean-nested repair verify all

help:
	@echo "ASCON repo targets"
	@echo ""
	@echo "  make test                 Run root tests only"
	@echo "  make test-all             Same as test; pytest.ini prevents nested collection"
	@echo "  make test-kat             Run known-answer tests"
	@echo "  make test-spec            Run spec/model tests"
	@echo "  make test-arch            Run architecture/config tests"
	@echo "  make generate-verilog     Regenerate rtl/generated/*.v[h]"
	@echo "  make list-configs         Print selected valid configs"
	@echo "  make docs-configs         Write config reports under docs/generated/"
	@echo "  make design-asic          Generate default ASIC design product"
	@echo "  make design-fpga          Generate default FPGA N-engine product"
	@echo "  make design-fpga-pipeline Generate 1-pipeline/N-context FPGA product"
	@echo "  make design-fpga-mpipelines Generate M-pipeline/N-context FPGA product"
	@echo "  make matrix               Generate selected ASIC/FPGA design matrix"
	@echo "  make clean                Remove caches, build products, generated docs/RTL"
	@echo "  make clean-nested         Remove known nested old repo folders/zips"
	@echo "  make repair               clean-nested + clean, then test"
	@echo "  make verify               Run tests, config docs, and Verilog generation"
	@echo ""
	@echo "Variables: PYTHON, PYTEST_FLAGS, ENGINE_COUNT, PIPELINE_COUNT, CONTEXTS_PER_ENGINE, BUILD_DIR"

env:
	@$(PYTHON) --version
	@$(PYTHON) -m pytest --version

check-layout:
	@test -d ascon_hwmodel || (echo "Missing ascon_hwmodel/. Run from the repo root."; exit 1)
	@test -d tests || (echo "Missing tests/. Run from the repo root."; exit 1)
	@if [ -d ignore ]; then echo "Warning: ignore/ exists. pytest.ini ignores it; run 'make clean-nested' to delete it."; fi
	@if [ -d ascon_hwmodel_aead_hash_step ]; then echo "Warning: nested ascon_hwmodel_aead_hash_step/ exists. pytest.ini ignores it; run 'make clean-nested' to delete it."; fi

test: check-layout clean-cache
	$(PYTHON) -m pytest $(PYTEST_FLAGS) tests

test-all: test

test-kat: check-layout clean-cache
	$(PYTHON) -m pytest $(PYTEST_FLAGS) tests/test_known_answer_vectors.py

test-spec: check-layout clean-cache
	$(PYTHON) -m pytest $(PYTEST_FLAGS) \
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
	@if [ -d ascon_arch ]; then \
		$(PYTHON) -m pytest $(PYTEST_FLAGS) \
			tests/test_arch_config.py \
			tests/test_example_configs_validate.py \
			tests/test_valid_config_listing.py \
			tests/test_control_profiles.py \
			tests/test_padding_profiles.py \
			tests/test_security_profiles.py \
			tests/test_top_level_profiles.py; \
	else \
		echo "No ascon_arch/ directory; skipping architecture tests."; \
	fi

generate-verilog: check-layout
	$(PYTHON) tools/generate_verilog.py

list-configs: check-layout
	$(PYTHON) tools/list_valid_configs.py --target both

docs-configs: check-layout
	@mkdir -p docs/generated
	$(PYTHON) tools/list_valid_configs.py --target both --format csv --out docs/generated/selected_valid_configs.csv
	$(PYTHON) tools/list_valid_configs.py --target both --format json --include-invalid --out docs/generated/selected_config_validation_report.json
	$(PYTHON) tools/list_valid_configs.py --target both --format text --out docs/generated/selected_valid_configs.txt

design-asic: check-layout
	$(PYTHON) tools/generate_design.py --preset asic_dual_enc_dec_cores --out $(BUILD_DIR)

design-fpga: check-layout
	$(PYTHON) tools/generate_design.py --preset fpga_n_parallel_engines --engine-count $(ENGINE_COUNT) --out $(BUILD_DIR)

design-fpga-pipeline: check-layout
	$(PYTHON) tools/generate_design.py \
		--preset fpga_one_pipelined_permutation_n_contexts \
		--contexts-per-engine $(CONTEXTS_PER_ENGINE) \
		--out $(BUILD_DIR)

design-fpga-mpipelines: check-layout
	$(PYTHON) tools/generate_design.py \
		--preset fpga_m_pipelines_n_contexts \
		--engine-count $(PIPELINE_COUNT) \
		--contexts-per-engine $(CONTEXTS_PER_PIPELINE) \
		--out $(BUILD_DIR)

matrix: check-layout
	$(PYTHON) tools/generate_matrix.py --target both --engine-count $(ENGINE_COUNT) --out $(BUILD_DIR)/matrix --write-invalid-report

clean-cache:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	@find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	@rm -rf .mypy_cache .ruff_cache htmlcov .coverage

clean-build:
	@rm -rf $(BUILD_DIR)

clean-generated:
	@mkdir -p rtl/generated docs/generated
	@find rtl/generated -type f ! -name .gitkeep -delete
	@find docs/generated -type f ! -name .gitkeep -delete
	@touch rtl/generated/.gitkeep docs/generated/.gitkeep

clean-nested:
	@rm -rf ignore
	@rm -rf ascon_hwmodel_aead_hash_step
	@rm -f ascon_hwmodel_aead_hash_step.zip repo.zip

clean: clean-cache clean-build clean-generated

repair: clean-nested clean test

verify: test docs-configs generate-verilog

all: verify design-asic design-fpga design-fpga-pipeline design-fpga-mpipelines
