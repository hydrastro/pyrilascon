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

ENV := PYTHONPATH=.
PY := $(ENV) $(PYTHON)
PYTEST_CMD := $(ENV) $(PYTEST)

.PHONY: help env check-layout test test-all test-kat test-spec test-arch \
        generate-verilog list-configs list-configs-csv list-configs-json docs-configs \
        stream-encrypt-sim stream-decrypt-sim matrix design-asic design-fpga design-fpga-pipeline design-fpga-mpipelines \
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
	$(PY) tools/run_stream_encrypt_vector.py --key-hex 000102030405060708090a0b0c0d0e0f --nonce-hex 101112131415161718191a1b1c1d1e1f --ad-hex aabbccddeeff --plaintext-hex 000102030405060708090a0b0c0d0e0f101112

stream-decrypt-sim: check-layout
	$(PY) tools/run_stream_decrypt_vector.py --key-hex 000102030405060708090a0b0c0d0e0f --nonce-hex 101112131415161718191a1b1c1d1e1f --ad-hex aabbccddeeff --plaintext-hex 000102030405060708090a0b0c0d0e0f101112
	$(PY) tools/run_stream_decrypt_vector.py --corrupt-tag --key-hex 000102030405060708090a0b0c0d0e0f --nonce-hex 101112131415161718191a1b1c1d1e1f --ad-hex 6d65746164617461 --plaintext-hex 73656372657420706c61696e74657874

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
